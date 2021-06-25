#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
<plugin key="xfr_buienalarm" name="Buienalarm" author="Xorfor" version="1.0" wikilink="https://github.com/Xorfor/Domoticz-Buienalarm-Plugin" externallink="https://www.buienalarm.nl/">
    <params>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal" default="true"/>
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
import json
from datetime import datetime
from datetime import timedelta
import time
from enum import IntEnum, unique  # , auto


@unique
class unit(IntEnum):
    """
    Device Unit numbers

    Define here your units numbers. These can be used to update your devices.
    Be sure the these have a unique number!
    """

    RAIN = 1
    TEXT = 2
    ALERT = 3
    TEMP = 4


@unique
class used(IntEnum):
    """
    Constants which can be used to create the devices. Look at onStart where
    the devices are created.
        used.NO, the user has to add this device manually
        used.YES, the device will be directly available
    """

    NO = 0
    YES = 1


class BasePlugin:

    __PRECIP_TIME = "{:%H:%M}"

    # Next lines
    __NO_PRECIP = "Geen neerslag"
    __PRECIP = "Neerslag"
    __PRECIP_START = "Neerslag begint rond " + __PRECIP_TIME
    __PRECIP_STOP = "Neerslag stopt rond " + __PRECIP_TIME
    __PRECIP_AGAIN = " en begint weer rond " + __PRECIP_TIME
    __PRECIP_DURATION = " en duurt ongeveer tot " + __PRECIP_TIME

    __DEBUG_NONE = 0
    __DEBUG_ALL = 1

    __HEARTBEATS2MIN = 6
    __MINUTES = 5  # Data is updated every 5 minutes

    """
    Full url:
        https://cdn-secure.buienalarm.nl/api/3.4/forecast.php?lat={}&lon={}&region=nl&unit=mm/u

    Example of data:

    {
        "success": true,
        "start": 1624642500,
        "start_human": "19:35",
        "temp": 19,
        "delta": 300,
        "precip": [
            0.19,
            0.12,
            0.09,
            0.04,
            0.03,
            0.02,
            0.01,
            0.01,
            0.03,
            0.02,
            0.01,
            0,
            0,
            0,
            0.05,
            0.1,
            0.05,
            0.03,
            0.02,
            0,
            0,
            0,
            0,
            0,
            0.01
        ],
        "levels": {
            "light": 0.25,
            "moderate": 1,
            "heavy": 2.5
        },
        "grid": {
            "x": 328,
            "y": 395
        },
        "source": "nl",
        "bounds": {
            "N": 55.973602,
            "E": 10.856429,
            "S": 48.895302,
            "W": 0
        }
    }

    """

    __API_CONN = "buienalarm"
    __API_ENDPOINT = "cdn-secure.buienalarm.nl"
    __API_VERSION = "/api/3.4"
    __API_PARAMETERS = "/forecast.php?lat={}&lon={}&region={}&unit=mm/u"
    #
    __API_URL = __API_VERSION + __API_PARAMETERS

    __UNITS = [
        # Unit, Name, Type, Subtype, Options, Used
        [unit.ALERT, "Alert", 243, 22, {}, 1],
        [unit.RAIN, "Rain", 85, 1, {"0;0"}, 1],
        [unit.TEXT, "Text", 243, 19, {}, 1],
        [unit.TEMP, "Temperature", 80, 5, {}, 1],
    ]

    def __init__(self):
        self.__runAgain = 0
        self.__url = ""
        self.__conn = None

    def onStart(self):
        Domoticz.Log("onStart")
        # Set Debug mode
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(self.__DEBUG_ALL)
        else:
            Domoticz.Debugging(self.__DEBUG_NONE)
        self.__region = "nl"
        # Get Domoticz location
        loc = Settings["Location"].split(";")
        self.__lat = float(loc[0])
        self.__lon = float(loc[1])
        if self.__lat is None or self.__lon is None:
            Domoticz.Error("Unable to parse coordinates")
            return False
        self.__url = self.__API_URL.format(self.__lat, self.__lon, self.__region)
        # Create devices
        for unit in self.__UNITS:
            if unit[0] not in Devices:
                Domoticz.Device(
                    Unit=unit[0],
                    Name=unit[1],
                    Type=unit[2],
                    Subtype=unit[3],
                    Options=unit[4],
                    Used=unit[5],
                ).Create()
        DumpAllToLog()
        # Setup connection
        self.__conn = Domoticz.Connection(
            Name=self.__API_CONN,
            Transport="TCP/IP",
            Protocol="HTTPS",
            Address=self.__API_ENDPOINT,
            Port="443",
        )
        self.__conn.Connect()

    def onStop(self):
        Domoticz.Debug("onStop")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug(
            "onConnect: {}, {}, {}".format(Connection.Name, Status, Description)
        )

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage: {}, {}".format(Connection.Name, Data))
        if Connection.Name == self.__API_CONN:
            if int(Data["Status"]) == 200:
                values = json.loads(Data["Data"].decode("utf-8", "ignore"))
                Domoticz.Debug("onMessage (values): {}".format(values))

                # Temperature
                temp = values.get("temp")
                UpdateDevice(unit.TEMP, 0, "{}".format(temp))

                t = values.get("start_human")  # start time for precipitation
                d = values.get("delta")  # interval precipitation is reported
                Domoticz.Debug("onMessage (t): {}".format(t))
                Domoticz.Debug("onMessage (d): {}".format(d))
                now = datetime.now()
                startData = now.strftime("%Y-%m-%d") + " " + t
                # Avoid bug in Python
                try:
                    brDT = datetime.strptime(startData, "%Y-%m-%d %H:%M")
                except TypeError:
                    brDT = datetime(*(time.strptime(startData, "%Y-%m-%d %H:%M")[0:6]))
                Domoticz.Debug("brDT: " + str(brDT))
                precip = values.get("precip", [])
                Domoticz.Debug("precip: " + str(precip))

                # Create text describing the expected precipitation
                raining = 0
                maxP = 0
                maxDT = None
                status = ""
                i = 0
                j = 0
                # Loop through the precipitation list. One value each delta=300 (seconds = 5 minutes)
                for p in precip:
                    dt = brDT + timedelta(seconds=i * d)
                    i += 1
                    # We are sometimes also getting 'old' data. Skip this!
                    if dt >= now:
                        j += 1
                        # Domoticz.Debug("{}: {}".format(dt, p))
                        """
                        0: Geen neerslag
                        1: Neerslag
                        2: Neerslag stopt rond {}
                        3: Neerslag stopt rond {} <+> en begint weer rond {}
                        4: Neerslag begint rond {}
                        5: Neerslag begint rond {} <+> en duurt ongeveer tot {}
                        """
                        if j == 1:
                            if p == 0:
                                # Currently no rain
                                raining = 0
                                status = self.__NO_PRECIP
                            else:
                                # It is raining now
                                raining = 1
                                status = self.__PRECIP
                            # Display current rain
                            UpdateDevice(unit.RAIN, 0, "{};{}".format(100 * p, 0))
                        else:
                            if raining == 0:
                                if p > 0:
                                    # Rain starts within 2 hours
                                    raining = 4
                                    # start = dt
                                    status = self.__PRECIP_START.format(dt)
                            elif raining == 1:
                                if p == 0:
                                    # It is currently raining but will stop within 2 hours
                                    raining = 2
                                    # end = dt
                                    status = self.__PRECIP_STOP.format(dt)
                            elif raining == 2:
                                if p > 0:
                                    # Raining will stop but restart within 2 hours
                                    raining = 3
                                    # start = dt
                                    status += self.__PRECIP_AGAIN.format(dt)
                            elif raining == 4:
                                if p == 0:
                                    # Rain starts within 2 hours but will stop
                                    raining = 5
                                    # end = dt
                                    status += self.__PRECIP_DURATION.format(dt)
                        if p > maxP:
                            maxP = p
                            maxDT = dt
                    else:
                        pass
                        # Domoticz.Debug("Now: {}".format(now))
                        # Domoticz.Debug("startData: {}".format(startData))
                # Looped through precipitation, so update device
                UpdateDevice(unit.TEXT, 0, status)

                # Precipitation Alert
                """
                Precipitation Alert:

                zware buien > 10
                zware neerslag 3-10 mm
                matige neerslag 1-3 mm
                lichte neerslag 0.1-1 mm
                geen neerslag 0 mm
                """
                maxP = round(maxP, 1)
                if maxP < 0.1:
                    alertLevel = 0
                    alertText = "Geen neerslag"
                elif maxP <= 1:
                    alertLevel = 1
                    alertText = "Lichte neerslag ({} mm/h @ {:%H:%M})".format(
                        maxP, maxDT
                    )
                elif maxP <= 3:
                    alertLevel = 2
                    alertText = "Matige neerslag ({} mm/h @ {:%H:%M})".format(
                        maxP, maxDT
                    )
                elif maxP <= 10:
                    alertLevel = 3
                    alertText = "Zware neerslag ({} mm/h @ {:%H:%M})".format(
                        maxP, maxDT
                    )
                elif maxP > 10:
                    alertLevel = 4
                    alertText = "Zware buien ({} mm/h @ {:%H:%M})".format(maxP, maxDT)
                UpdateDevice(unit.ALERT, alertLevel, alertText)

                Domoticz.Debug("# datapoints: {}/{}".format(j, i))

                # Temperature
            else:
                Domoticz.Debug("No data received")

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand: {}, {}, {}, {}".format(Unit, Command, Level, Hue))

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Debug(
            "onNotification: {}, {}, {}, {}, {}, {}, {}".format(
                Name, Subject, Text, Status, Priority, Sound, ImageFile
            )
        )

    def onDisconnect(self, Connection):
        Domoticz.Debug("onDisconnect: {}".format(Connection.Name))

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat")
        # Live
        self.__runAgain -= 1
        if self.__runAgain <= 0:
            if self.__conn.Connecting() or self.__conn.Connected():
                Domoticz.Debug("onHeartbeat ({}): is alive".format(self.__conn.Name))
                Domoticz.Debug("url: {}".format(self.__url))
                sendData = {
                    "Verb": "GET",
                    "URL": self.__url,
                    "Headers": {
                        "Host": self.__API_ENDPOINT,
                        "User-Agent": "Domoticz/1.0",
                    },
                }
                self.__conn.Send(sendData)
            else:
                self.__conn.Connect()
            self.__runAgain = self.__HEARTBEATS2MIN * self.__MINUTES
        Domoticz.Debug(
            "onHeartbeat ({}): {} heartbeats".format(self.__conn.Name, self.__runAgain)
        )


global _plugin
_plugin = BasePlugin()


def onStart():
    global _plugin
    _plugin.onStart()


def onStop():
    global _plugin
    _plugin.onStop()


def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)


def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)


def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)


def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)


def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)


def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()


# Vervallen?
def value2mmph(value):
    if value > 0:
        return round(10 ** ((value - 109) / 32), 1)
    else:
        return 0


################################################################################
# Generic helper functions
################################################################################


def DumpDevicesToLog():
    # Show devices
    Domoticz.Debug("Device count.........: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device...............: " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device Idx...........: " + str(Devices[x].ID))
        Domoticz.Debug(
            "Device Type..........: "
            + str(Devices[x].Type)
            + " / "
            + str(Devices[x].SubType)
        )
        Domoticz.Debug("Device Name..........: '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue........: " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue........: '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device Options.......: '" + str(Devices[x].Options) + "'")
        Domoticz.Debug("Device Used..........: " + str(Devices[x].Used))
        Domoticz.Debug("Device ID............: '" + str(Devices[x].DeviceID) + "'")
        Domoticz.Debug("Device LastLevel.....: " + str(Devices[x].LastLevel))
        Domoticz.Debug("Device Image.........: " + str(Devices[x].Image))


def DumpImagesToLog():
    # Show images
    Domoticz.Debug("Image count..........: " + str(len(Images)))
    for x in Images:
        Domoticz.Debug("Image '" + x + "...': '" + str(Images[x]) + "'")


def DumpParametersToLog():
    # Show parameters
    Domoticz.Debug("Parameters count.....: " + str(len(Parameters)))
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("Parameter '" + x + "'...: '" + str(Parameters[x]) + "'")


def DumpSettingsToLog():
    # Show settings
    Domoticz.Debug("Settings count.......: " + str(len(Settings)))
    for x in Settings:
        Domoticz.Debug("Setting '" + x + "'...: '" + str(Settings[x]) + "'")


def DumpAllToLog():
    DumpDevicesToLog()
    DumpImagesToLog()
    DumpParametersToLog()
    DumpSettingsToLog()


def DumpHTTPResponseToLog(httpDict):
    if isinstance(httpDict, dict):
        Domoticz.Debug("HTTP Details (" + str(len(httpDict)) + "):")
        for x in httpDict:
            if isinstance(httpDict[x], dict):
                Domoticz.Debug("....'" + x + " (" + str(len(httpDict[x])) + "):")
                for y in httpDict[x]:
                    Domoticz.Debug("........'" + y + "':'" + str(httpDict[x][y]) + "'")
            else:
                Domoticz.Debug("....'" + x + "':'" + str(httpDict[x]) + "'")


def UpdateDevice(Unit, nValue, sValue, TimedOut=0, AlwaysUpdate=False):
    if Unit in Devices:
        if (
            Devices[Unit].nValue != nValue
            or Devices[Unit].sValue != sValue
            or Devices[Unit].TimedOut != TimedOut
            or AlwaysUpdate
        ):
            Devices[Unit].Update(nValue=nValue, sValue=str(sValue), TimedOut=TimedOut)
            Domoticz.Debug(
                "Device update "
                + Devices[Unit].Name
                + ": "
                + str(nValue)
                + " - '"
                + str(sValue)
                + "'"
            )


def UpdateDeviceOptions(Unit, Options={}):
    if Unit in Devices:
        if Devices[Unit].Options != Options:
            Devices[Unit].Update(
                nValue=Devices[Unit].nValue,
                sValue=Devices[Unit].sValue,
                Options=Options,
            )
            Domoticz.Debug(
                "Device Options update: " + Devices[Unit].Name + " = " + str(Options)
            )


def UpdateDeviceImage(Unit, Image):
    if Unit in Devices and Image in Images:
        if Devices[Unit].Image != Images[Image].ID:
            Devices[Unit].Update(
                nValue=Devices[Unit].nValue,
                sValue=Devices[Unit].sValue,
                Image=Images[Image].ID,
            )
            Domoticz.Debug(
                "Device Image update: "
                + Devices[Unit].Name
                + " = "
                + str(Images[Image].ID)
            )
