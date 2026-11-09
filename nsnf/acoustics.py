"""Native PCM evidence extraction; no linguistic or psychological interpretation."""
from io import BytesIO
import wave
import numpy as np


def analyze_wav(data):
    if len(data) > 16 * 1024 * 1024:
        raise ValueError("audio exceeds 16 MiB")
    try:
        with wave.open(BytesIO(data), 'rb') as audio:
            channels, width, rate, count = audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getnframes()
            if channels not in (1, 2) or width != 2 or not 8000 <= rate <= 48000:
                raise ValueError("16-bit PCM WAV, mono/stereo, 8–48 kHz required")
            if not 0 < count <= rate * 30:
                raise ValueError("audio duration must be greater than zero and at most 30 seconds")
            raw = audio.readframes(count)
    except (wave.Error, EOFError) as error:
        raise ValueError("invalid PCM WAV") from error
    if len(raw) != count * channels * width:
        raise ValueError("truncated audio frames")
    native = np.frombuffer(raw, dtype='<i2').reshape(-1, channels).astype(np.float64) / 32768
    mono = native.mean(axis=1)
    size = max(1, round(rate * .02))
    frames = []
    for offset in range(0, len(mono), size):
        signal = mono[offset:offset + size]
        spectrum = abs(np.fft.rfft(signal * np.hanning(len(signal))))
        frequencies = np.fft.rfftfreq(len(signal), 1 / rate)
        mass = float(spectrum.sum())
        rms = float(np.sqrt(np.mean(signal * signal)))
        centroid = float(np.dot(frequencies, spectrum) / mass) if mass else 0.
        # Autocorrelation periodicity is a candidate F0, distinct from phonological tone.
        centered = signal - signal.mean()
        correlation = np.correlate(centered, centered, mode='full')[len(centered)-1:]
        low, high = max(1, rate // 1000), min(len(correlation), rate // 60)
        pitch = None
        periodicity = 0.
        if high > low and correlation[0] > 1e-12:
            lag = low + int(np.argmax(correlation[low:high]))
            periodicity = float(correlation[lag] / correlation[0])
            if periodicity >= .5 and rms > .005:
                pitch = float(rate / lag)
        frames.append({'start_s': offset / rate, 'end_s': (offset + len(signal)) / rate,
                       'rms_amplitude': rms, 'spectral_centroid_hz': centroid,
                       'candidate_f0_hz': pitch, 'periodicity': periodicity,
                       'boundary': 'frame boundary only; no phoneme or semantic segmentation'})
    rms = float(np.sqrt(np.mean(mono * mono)))
    peaks = float(np.max(abs(native)))
    duration = count / rate
    zero_crossings = float(np.mean(np.signbit(mono[1:]) != np.signbit(mono[:-1]))) if count > 1 else 0.
    mean_centroid = float(np.mean([f['spectral_centroid_hz'] for f in frames]))
    pitches = [f['candidate_f0_hz'] for f in frames if f['candidate_f0_hz'] is not None]
    return {'decoder': 'stdlib-wave-pcm16-v1', 'sample_rate_hz': rate, 'channels': channels,
            'sample_count': count, 'duration_s': duration, 'frames': frames,
            'features': {'rms_amplitude': rms, 'peak_amplitude': peaks,
                         'zero_crossing_fraction': zero_crossings, 'mean_spectral_centroid_hz': mean_centroid},
            'neural_features': [rms, peaks, zero_crossings, mean_centroid / (rate / 2), duration / 30,
                                len(pitches) / len(frames), channels / 2, 1.],
            'units': {'amplitude': 'normalized PCM full scale; not calibrated physical intensity',
                      'time': 'seconds from artifact start', 'frequency': 'hertz'},
            'unknown': ['words', 'phonemes', 'linguistic tone', 'meaning', 'emotion', 'intent', 'HD Tone'],
            'status': 'measured acoustic features only'}
