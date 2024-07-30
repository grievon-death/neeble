import json
import logging
import requests
from collections import namedtuple

from settings.config import OW_API_CONFIG

def getweatherdata(city:str):
    """
    Gets weather data based on coordinates
    """
    ow_wh_url = OW_API_CONFIG['wh_url'].encode('utf-8').decode('utf-8')
    ow_wh_url = ow_wh_url.replace('<CITY>', city)
    ow_wh_url = ow_wh_url.replace('<API_ID>', OW_API_CONFIG['api_id'])
    ow_wh_url = ow_wh_url.encode('utf-8').decode('utf-8')

    weatherdata = requests.get(ow_wh_url).text
    weatherdata = weatherdata.encode('utf-8').decode('utf-8')
    weatherdata = json.loads(weatherdata)

    return weatherdata

def displayweather(wdata) -> object:
    """
    "Prettifies" the output for discord
    """
    try:
        description = wdata['weather'][0]['description']
    except:
        description = None

    try:
        icon = wdata['weather'][0]['icon']
        condition = icon[:2]
        time = icon[2:]
        match time:
            case 'd':
                match condition:
                    case '01':
                        icon = ':sunny:'
                    case '02':
                        icon = ':white_sun_cloud:'
                    case '03':
                        icon = ':cloud:'
                    case '04':
                        icon = ':cloud:'
                    case '09':
                        icon = ':cloud_rain:'
                    case '10':
                        icon = ':white_sun_rain_cloud:'
                    case '11':
                        icon = ':cloud_lightning:'
                    case '13':
                        icon = ':snowflake:'
                    case '50':
                        icon = ':fog:'
            case 'n':
                match condition:
                    case '01':
                        icon = ':full_moon:'
                    case '02':
                        icon = ':cloud:'
                    case '03':
                        icon = ':cloud:'
                    case '04':
                        icon = ':cloud:'
                    case '09':
                        icon = ':cloud_rain:'
                    case '10':
                        icon = ':white_sun_rain_cloud:'
                    case '11':
                        icon = ':thunder_cloud_rain:'
                    case '13':
                        icon = ':snowflake:'
                    case '50':
                        icon = ':fog:'
    except:
        icon = None

    try:
        tempmsg = wdata['main']['temp']
    except:
        tempmsg = None

    try:
        feels_likemsg = wdata['main']['feels_like']
    except:
        feels_likemsg = None

    try:
        humiditymsg = wdata['main']['humidity']
    except:
        humiditymsg = None

    try:
        wind_speedmsg = wdata['wind']['speed']
    except:
        wind_speedmsg = None

    try:
        wind_gustsmsg = wdata['wind']['gust']
    except:
        wind_gustsmsg =  None
    try:
        cloud_coveragemsg = wdata['clouds']['all']
    except:
        cloud_coveragemsg = None

    name = wdata['name']
    obj = namedtuple('Weather', [
        'name',
        'description',
        'icon',
        'temp',
        'feels_like',
        'humidity',
        'wind_speed',
        'wind_gusts',
        'cloud_coverage',
    ])
    weather = obj(*(
        name,
        description,
        icon,
        tempmsg,
        feels_likemsg,
        humiditymsg,
        wind_speedmsg,
        wind_gustsmsg,
        cloud_coveragemsg
    ))

    return weather
