import numpy as np

def batch(data, batch_size, fill=False):
  '''
  Transform data from (sample, feature) into (batch, sample, feature)
  '''
  # Find out how many extra samples we have and remove them
  extra = data.shape[0] % batch_size
  if extra != 0:
    data = data[:-extra,:]
  
  return data.reshape((-1, batch_size, data.shape[1]))