from __future__ import division
import numpy as np
from datetime import datetime, timedelta
import time
import pyaudio

class PrerecordedDataSource(object):
    CHANNEL_TICK = 0
    CHANNEL_PPS  = 1

    def __init__(self, filename):
        self.filename = filename

        print "Loading pre-recorded data from %s..." % filename
        data = np.load(filename)
        self.fs = data['fs']
        self.y = data['signal']
        self.start_time = datetime.fromtimestamp(data['start_time'])
        self.i = 0

    def get_samples(self, num_samples):
        """Return some samples"""
        if self.i >= self.y.shape[0]:
            raise EOFError
        samples = self.y[self.i : (self.i + num_samples)]
        return samples

    def consume(self, num_samples):
        """Mark num_samples as having been used"""
        self.i += num_samples

    @property
    def time(self):
        """Time of first available sample"""
        return self.start_time + timedelta(seconds = self.i / self.fs)

class SoundCardDataSource(object):
    CHANNEL_TICK = 0
    CHANNEL_PPS  = 1

    def __init__(self, sampling_rate=44100):
        self.fs = sampling_rate

        self.pyaudio_manager = pyaudio.PyAudio()
        self.stream = self.pyaudio_manager.open(
            format=pyaudio.paInt16, channels=2, rate=sampling_rate, input=True)

        self.buffer = np.empty((0, 2))
        self.buffer_start_time = None

    def __del__(self):
        print "@@@@@@@ closing @@@@@@@@"
        self.stream.stop_stream()
        self.stream.close()
        self.pyaudio_manager.terminate()

    def read(self, num_samples):
        raw_data = self.stream.read(num_samples)
        samples = (np.frombuffer(raw_data, dtype=np.int16).reshape((-1,2))
            .astype(float) / 2**15)
        return samples

    def get_samples(self, num_samples):
        """Return some samples"""
        num_to_read = num_samples - self.buffer.shape[0]
        if num_to_read > 0:
            new_samples = self.read(num_to_read)
            self.buffer = np.r_[ self.buffer, new_samples ]
            self.buffer_start_time = \
                datetime.utcnow() - timedelta(seconds=self.buffer.shape[0]/self.fs)
        return self.buffer[:num_samples]

    def consume(self, num_samples):
        """Mark num_samples as having been used"""
        num_to_read = num_samples - self.buffer.shape[0]
        if num_to_read > 0:
            self.get_samples(num_to_read)
        assert self.buffer.shape[0] >= num_samples
        self.buffer = self.buffer[num_samples:]

    @property
    def time(self):
        """Time of first available sample"""
        return self.buffer_start_time