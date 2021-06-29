from statsmodels import api as sm
import pandas as pd
import numpy as np
import sweat
import scipy.fft


class Gps():
    def __init__(self, path):
      self.data = sweat.read_fit(path)
      self.data.speed *= (3600*1e-3)
      self.lapLen = self.get_lap_len()
      self.offset = 0
      self.stat = self.compute_data_by_lap()

    def set_offset(self, offset):
      self.offset = offset
      self.stat = self.compute_data_by_lap()


    def get_lap_len(self):
      """
      Find GPS laps in data.
      """
      distance = np.linspace(0, np.max(self.data.distance.values), len(self.data.distance.values))
      interLat = np.interp(distance, self.data.distance.values, self.data.latitude.values)
      acf = sm.tsa.acf(interLat, nlags=len(interLat))
      lapLen = distance[np.argmax(acf[np.argmin(acf)::]) + np.argmin(acf)]
      return lapLen

    def get(self, key):
      if key in self.data.columns:
        return self.data[key].values
      else:
        return np.zeros(self.data.distance.values.shape)

    def compute_data_by_lap(self):
      """
      Compute and plot stat by lap.
      Gps is true mean that lap are autodetected by gps.
      """
      stat = {}
      count = 0
      dist = self.offset
      while dist + self.lapLen < self.get("distance")[-1]:
        data = self.data[ (self.data.distance.values >= dist) & (self.data.distance.values < dist + self.lapLen) ]
        tmp = {}
        for i in ["speed", "cadence", "heartrate", "power"]:
          if i in data.columns:
            tmp[i] = {"min": np.nanmin(data[i].values), "max": np.nanmax(data[i].values), "mean": np.nanmean(data[i].values)}
          else:
            tmp[i] = {"min": 0, "max": 0, "mean": 0}
        stat["lap_" + str(count)] = tmp
        count += 1
        dist += self.lapLen
      return stat


    def get_short_summary(self, lap=None):
      summary = []
      for j, i in enumerate(self.stat.keys()):
        summary.append(" Lap: {lap} \n speed: {speed} \n heartrate: {hr} \n cadence: {cd} \n power: {pw} \n".format(lap = str(j), speed= str(np.around(self.stat[i]["speed"]["mean"], 1)), hr= str(np.around(self.stat[i]["heartrate"]["mean"], 1)), cd= str(np.around(self.stat[i]["cadence"]["mean"], 1)), pw=str(np.around(self.stat[i]["power"]["mean"], 1))))
      if lap != None:
        return summary[lap]
      else:
        return summary
