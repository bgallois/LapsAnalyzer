from statsmodels import api as sm
import pandas as pd
import numpy as np
import sweat
import scipy.fft


class Gps():
    def __init__(self, path):
      self.data = sweat.read_fit(path)
      self.offSet = 0
      self.lapLen = self.get_lap_len()

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
      pass
