#!/usr/bin/python3
import requests
import json
from time import sleep
import configparser
import logging
import argparse


logger = logging.getLogger("bandwidth_use")
logger.setLevel(logging.DEBUG)
logfile_handler = logging.FileHandler("bandwidth.log")
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
logfile_handler.setFormatter(formatter)
logger.addHandler(logfile_handler)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.info("Starting script, polling router for the first time")

config = configparser.ConfigParser()
config.read("config.txt")
payload = {"user" : config["CREDS"]["username"], "pws" : config["CREDS"]["password"], "remember_me" : config["CREDS"]["remember_me"]}
router = config["CREDS"]["router_ip"]

referer_login = "http://{0}/login.html".format(router)
login_url = "http://{0}/goform/login".format(router)


def parse_args():
    parser = argparse.ArgumentParser(description="A script to interface with a Hitron CODA router/modem")
    parser.add_argument("--download_usage", "-u", action="store_true")
    parser.add_argument("--download_rate", "-r", action="store_true")
    parser.add_argument("--ip", "-i", action="store_true")
    parser.add_argument("--dns", "-d", action="store_true")
    args = parser.parse_args()
    return args


# check connectivity and log in to router
def connectivity_check():
    session_requests = requests.session()
    result = session_requests.post(login_url, data = payload, headers = dict(referer = referer_login))

    if result.status_code == 200:
        return session_requests
    else:
        return False


# get amount downloaded so far this month, and account for metric prefix (put everything in GB)
def monthly_downloaded(authenticated_session):
    bandwidth = authenticated_session.get("http://{0}/data/getSysInfo.asp".format(router))
    try:
        parsed = json.loads(bandwidth.content)
        downloaded_old = parsed[0]["WRecPkt"].split(" ", 1)[0]
        if downloaded_old[-1] == "T":
            float_downloaded = float(downloaded_old.replace("T", "")) * 1024
        elif downloaded_old[-1] == "M":
            float_downloaded = float(downloaded_old.replace("M", "")) / 1024
        elif downloaded_old[-1] == "G":
            float_downloaded = float(downloaded_old.replace("G", ""))
        else:
            raise
        return float_downloaded
    except:
        return False


def check_ip(authenticated_session):
    data = authenticated_session.get("http://{0}/data/getSysInfo.asp".format(router))
    try:
        parsed = json.loads(data.content)
        return parsed[0]["wanIp"]
    except:
        return False


def check_dns(authenticated_session):
    data = authenticated_session.get("http://{0}/data/getSysInfo.asp".format(router))
    try:
        parsed = json.loads(data.content)
        return [parsed[0]["priDNS"], parsed[0]["secDNS"]]
    except:
        return False


def main():
    args = parse_args()
    connected = False
    first_loop = True
    while True:
        if not first_loop:
            sleep(3600)

        if not connected:
            auth_session = connectivity_check()
            if auth_session:
                logger.info("Got status code 200, router is up")
                connected = True
            else:
                logger.warn("Router is down or script was unable to authenticate, check connectivity")
                sleep(30)
                continue

        if args.download_usage:
            downloaded = monthly_downloaded(auth_session)
            if not downloaded:
                logging.warn("Unable to load JSON data from router")
                connected = False
                continue
            else:
                logger.info("Current download usage: " + str(downloaded) + "GB")

        if args.download_rate:
            downloaded = monthly_downloaded(auth_session)
            if not downloaded:
                logging.warn("Unable to load JSON data from router")
                connected = False
                continue
            if first_loop:
                last_downloaded = downloaded
                first_loop = False
            else:
                rate = round(downloaded - last_downloaded, 2)
                logger.info("Downloaded rate in last hour: " + str(rate))
                last_downloaded = downloaded

        if args.ip:
            ip = check_ip(auth_session)
            if not ip:
                logging.warn("Unable to load JSON data from router")
                connected = False
                continue
            else:
                logger.info("Current WAN IP: " + str(ip))

        if args.dns:
            dns_servers = check_dns(auth_session)
            if not dns_servers:
                logging.warn("Unable to load JSON data from router")
                connected = False
                continue
            else:
                logger.info("Primary DNS Server: " + dns_servers[0])
                logger.info("Secondary DNS Server: " + dns_servers[1])
        
        first_loop = False


if __name__ == "__main__":
    main()
