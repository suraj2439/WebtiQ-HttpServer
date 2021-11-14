import configparser

config = configparser.ConfigParser()
config.read("conf/server.conf")



SERVER_PORT = 7000
MAX_CONN = 100
MAX_REQ = 50
MAX_URI_LENGTH = 500
MAX_HEADER_LENGTH = 500
TIME_DIFF = 19800
SUPPORTED_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD"]
DEFAULT_DIR_PATH = "/home/suraj/Documents/study/TY/CN/Project/test"
EXPIRE_TIME = 86400
MAX_KEEP_ALIVE_TIME = 3 # in seconds
TOT_COUNT = 20
ACCESS_LOG_PATH = DEFAULT_DIR_PATH + "log/access.log"
COOKIE_EXPIRE_TIME = 60 #TODO
MY_COOKIE_NAME = "MyHttpCookie"
MAX_REQ_ON_PERSISTENT_CONN = 100
LOG_LEVEL = "all"

if "SERVER" in config.sections():
    DEFAULT_DIR_PATH = config["SERVER"]["DocumentRoot"]
    SERVER_PORT = int(config["SERVER"]["ServerPort"])
    MAX_CONN = int(config["SERVER"]["MaxSimultaneousConnections"])
    MAX_URI_LENGTH = int(config["SERVER"]["MaxUriLength"])
    MAX_HEADER_LENGTH = int(config["SERVER"]["MaxHeaderLength"])
    EXPIRE_TIME = int(config["SERVER"]["CacheExpireTime"])
    MAX_REQ_ON_PERSISTENT_CONN = int(config["SERVER"]["MaxReqOnPersistentConn"])

if "COOKIE" in config.sections():
    MY_COOKIE_NAME = config["COOKIE"]["CookieName"]
    MAX_KEEP_ALIVE_TIME = int(config["COOKIE"]["CookieExpireTime"])

if "LOG" in config.sections():
    ACCESS_LOG_PATH = config["LOG"]["AccessLogPath"]
    ERROR_LOG_PATH = config["LOG"]["ErrorLogPath"]
    LOG_LEVEL = config["LOG"]["LogLevel"]
