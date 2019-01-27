#!/usr/bin/python3
import requests
import json
import time
import configparser
import logging

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
config.read("config.config")

payload = {"user" : config["CREDS"]["username"], "pws" : config["CREDS"]["password"], "remember_me" : config["CREDS"]["remember_me"]}
router = config["CREDS"]["router_ip"]

referer_login = "http://{0}/login.html".format(router)
login_url = "http://{0}/goform/login".format(router)

# test connectivity and log in to router
while True:
    session_requests = requests.session()
    result = session_requests.post(login_url, data = payload, headers = dict(referer = referer_login))
    if result.status_code == 200:
        logger.info("Got status code 200, router is up")
        break
    else:
        logger.warn("Router is down or script was unable to authenticate, check connectivity")
        time.sleep(30)

# check router for initial download value
while True:
    bandwidth = session_requests.get("http://{0}/data/getSysInfo.asp".format(router))
    try:
        parsed = json.loads(bandwidth.content)
        downloaded_old = parsed[0]["WRecPkt"].split(" ", 1)[0]
        if downloaded_old[-1] == "T":
            float_downloaded_old = float(downloaded_old.replace("T", "")) * 1024
        elif downloaded_old[-1] == "M":
            float_downloaded_old = float(downloaded_old.replace("M", "")) / 1024
        elif downloaded_old[-1] == "G":
            float_downloaded_old = float(downloaded_old.replace("G", ""))
        else:
            logger.warn("JSON data from router appears malformed, couldn't find metric prefix")
            raise

        break
    except:
        logging.warn("Unable to load JSON data from router")
        time.sleep(30)


# main loop to poll router every hour and find difference in amount downloaded
while True:
    time.sleep(3600)    # set to be 1 hour, change to whatever you want
    result = session_requests.post(login_url, data = payload, headers = dict(referer = referer_login))
    bandwidth = session_requests.get("http://{0}/data/getSysInfo.asp".format(router))
    try:
        parsed = json.loads(bandwidth.content)
        downloaded_new = parsed[0]["WRecPkt"].split(" ", 1)[0]
        if downloaded_new[-1] == "T":
            float_downloaded_new = float(downloaded_new.replace("T", "")) * 1024
        elif downloaded_new[-1] == "M":
            float_downloaded_new = float(downloaded_new.replace("M", "")) / 1024
        elif downloaded_new[-1] == "G":
            float_downloaded_new = float(downloaded_new.replace("G", ""))
        else:
            logger.warn("JSON data from router appears malformed, couldn't find metric prefix")
            raise
    except:
        logging.warn("Unable to load JSON data from router")

    rate = round(float_downloaded_new - float_downloaded_old, 2)
    logger.info(str(rate))
    float_downloaded_old = float_downloaded_new
