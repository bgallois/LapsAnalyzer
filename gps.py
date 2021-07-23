from statsmodels import api as sm
import pandas as pd
import numpy as np
import sweat


class Gps():
    def __init__(self, path, modeAuto=True):
        self.mode = modeAuto
        self.data = sweat.read_fit(path)
        self.data.speed *= (3600 * 1e-3)
        if not self.mode:
            self.laps = self.get_manual_laps()
            self.stat = self.compute_data_by_lap(self.mode)
        else:
            self.offset = 0
            self.laps = self.get_lap_len()
            self.stat = self.compute_data_by_lap(self.mode)

        if "cadence" not in self.data.columns:
            self.data["cadence"] = np.zeros(self.data["latitude"].values.size)
        if "power" not in self.data.columns:
            self.data["power"] = np.zeros(self.data["latitude"].values.size)
        if "speed" not in self.data.columns:
            self.data["speed"] = np.zeros(self.data["latitude"].values.size)
        if "heartrate" not in self.data.columns:
            self.data["heartrate"] = np.zeros(self.data["latitude"].values.size)

        self.cdZeros = self.data["cadence"] == 0
        self.pwZeros = self.data["power"] == 0
        self.spZeros = self.data["speed"] == 0

    def set_offset(self, offset):
        self.laps = self.get_lap_len()
        self.offset = offset
        self.stat = self.compute_data_by_lap(self.mode)

    def remove_zeros(self, cd=False, pw=False, sp=False):
        if cd:
            self.data["cadence"] = self.data["cadence"].replace(0, np.nan)
        else:
            self.data["cadence"][self.cdZeros.values] = 0
        if pw:
            self.data["power"] = self.data["power"].replace(0, np.nan)
        else:
            self.data["power"][self.pwZeros.values] = 0
        if sp:
            self.data["speed"] = self.data["speed"].replace(0, np.nan)
        else:
            self.data["speed"][self.spZeros.values] = 0

        self.stat = self.compute_data_by_lap(self.mode)


    def get_lap_len(self):
        """
        Find GPS laps in data.
        """
        distance = np.linspace(
            0, np.max(
                self.data.distance.values), len(
                self.data.distance.values))
        interLat = np.interp(
            distance,
            self.data.distance.values,
            self.data.latitude.values)
        acf = sm.tsa.acf(interLat, nlags=len(interLat), fft=False)
        lapLen = distance[np.argmax(acf[np.argmin(acf)::]) + np.argmin(acf)]
        laps = [self.offset]
        for i in range(int(distance[-1] / lapLen)):
            laps += [laps[-1] + lapLen]
        return laps

    def get_manual_laps(self):
        """
        Find manual laps in data.
        """
        laps = [0]
        for i in set(self.get("lap")):
            laps.append(
                self.data[self.data.lap.values == i].distance.values[-1])
        return laps

    def get(self, key, distMin=0, distMax=np.inf):
        data = self.data[(self.data.distance.values >= distMin) & (
            self.data.distance.values <= distMax)]
        if key in data.columns:
            return data[key].values
        else:
            return np.zeros(self.data.distance.values.shape)

    def compute_data_by_lap(self, mode):
        """
        Compute and plot stat by lap.
        Gps is true mean that lap are autodetected by gps.
        """
        stat = {}
        for i, j in enumerate(self.laps[0:-1]):
            data = self.data[(self.data.distance.values >= j) & (
                self.data.distance.values <= self.laps[i + 1])]
            tmp = {}
            tmp["duration"] = (data.index[-1] - data.index[0]
                               ) / np.timedelta64(1, 'm')
            for k in ["speed", "cadence", "heartrate", "power"]:
                if k in data.columns:
                    tmp[k] = {
                        "min": np.nanmin(
                            data[k].values), "max": np.nanmax(
                            data[k].values), "mean": np.nanmean(
                            data[k].values)}
                else:
                    tmp[k] = {"min": 0, "max": 0, "mean": 0}
            stat["lap_" + str(i)] = tmp

        return stat

    def get_short_summary(self, lap=None):
        summary = []
        for j, i in enumerate(self.stat.keys()):
            summary.append(
                " Lap: {lap} \n duration: {dur} min \n speed: {speed} km/h \n heartrate: {hr} bpm \n cadence: {cd} rpm \n power: {pw} W \n".format(
                    dur=str(np.around(self.stat[i]["duration"], 1)),
                    lap=str(j), speed=str(
                        np.around(
                            self.stat[i]["speed"]["mean"], 1)), hr=str(
                        np.around(
                            self.stat[i]["heartrate"]["mean"], 1)), cd=str(
                        np.around(
                            self.stat[i]["cadence"]["mean"], 1)), pw=str(
                        np.around(
                            self.stat[i]["power"]["mean"], 1))))
        if lap is not None:
            return summary[lap]
        else:
            return summary
