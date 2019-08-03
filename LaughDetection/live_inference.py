import tensorflow as tf
import keras
import csv
from datetime import datetime
import numpy as np
import tempfile
import os
from scipy.io import wavfile

from audioset import vggish_embeddings
from laugh_detector.microphone_stream import MicrophoneStream

flags = tf.app.flags

flags.DEFINE_string(
    'keras_model', 'Models/LSTM_SingleLayer_100Epochs.h5',
    'Path to trained keras model that will be used to run inference.')

flags.DEFINE_float(
    'sample_length', 30.0,
    'Length of audio sample to process in each chunk'
)

flags.DEFINE_string(
    'save_file', None,
    'Filename to save inference output to as csv. Leave empty to not save'
)

flags.DEFINE_bool(
    'print_output', True,
    'Whether to print inference output to the terminal'
)

flags.DEFINE_string(
    'recording_directory', None,
    'Directory where recorded samples will be saved'
    'If None, samples will not be saved'
)

flags.DEFINE_bool(
    'hue_lights', False,
    'Map output to Hue bulbs'
)

flags.DEFINE_string(
    'hue_IP', None,
    'IP address for the Hue Bridge'
)

flags.DEFINE_integer(
    'avg_window', 10,
    'Size of window for running mean on output'
)

FLAGS = flags.FLAGS

RATE = 16000
CHUNK = int(RATE * FLAGS.sample_length)  # 3 sec chunks


def set_light(lights, b_score, c_score):
    for l in lights[:2]:
        l.brightness = int(map_range(b_score, 0, 255))
        l.xy = list(map_range(c_score, np.array(blue_xy), np.array(white_xy)))


def map_range(x, s, e):
    d = e-s
    return s+d*x


if __name__ == '__main__':
    #loading the specific trained laughter detection model, can modify the flag for new model
    model = keras.models.load_model(FLAGS.keras_model)
    audio_embed = vggish_embeddings.VGGishEmbedder()

    if FLAGS.save_file:
        if os.path.exists(FLAGS.save_file):
            pass
        else:
            with open(FLAGS.save_file, 'w') as writeFile:
                writer = csv.writer(writeFile)
                if FLAGS.recording_directory:
                    row = ['Date', 'filepath', 'laugh_score', 'volume']
                    writer.writerow(row)
                else:
                    row = ['Date', 'laugh_score', 'volume']
                    writer.writerow(row)

    if FLAGS.hue_lights:
        from phue import Bridge

        b = Bridge(FLAGS.hue_IP)
        lights = b.lights[:2]

        blue_xy = [0.1691, 0.0441]
        white_xy = [0.4051, 0.3906]

    #need to investigate what this window is used for, taking half of the window length
    window = [0.5]*FLAGS.avg_window

    #using MicrophoneStream as context class, using stream object to process the data
    with MicrophoneStream(RATE, CHUNK) as stream:
        #stream.generator() function automatically processes the 10 second chunks and puts them in a generator
        audio_generator = stream.generator()
        for chunk in audio_generator:
            try:
                arr = np.frombuffer(chunk, dtype=np.int16)
                vol = np.sqrt(np.mean(arr**2))
                embeddings = audio_embed.convert_waveform_to_embedding(arr, RATE)
                p = model.predict(np.expand_dims(embeddings, axis=0))

                window.pop(0)
                window.append(p[0, 0])

                if FLAGS.hue_lights:
                    set_light(lights, 0.6, sum(window)/len(window))

                if FLAGS.print_output:
                    print(str(datetime.now()) + ' - Laugh Score: {0:0.6f} - vol:{1}'.format(p[0, 0], vol))

                if FLAGS.save_file:
                    with open(FLAGS.save_file, 'a') as writeFile:
                        writer = csv.writer(writeFile)
                        if (FLAGS.recording_directory is not None) & (p[0,0] > 30):
                            f = tempfile.NamedTemporaryFile(delete=False, suffix='.wav', dir=FLAGS.recording_directory)
                            wavfile.write(f, RATE, arr)
                            time_value = datetime.now().strftime("%b %d %Y %H:%M:%S")
                            row = [time_value, f.name, p[0,0], vol]
                            writer.writerow(row)
                        elif FLAGS.recording_directory:
                            time_value = datetime.now().strftime("%b %d %Y %H:%M:%S")
                            row = [time_value, 'not funny enough for saving', p[0,0], vol]
                            writer.writerow(row)
                        else:
                            with open(FLAGS.save_file, 'a') as writeFile:
                                writer = csv.writer(writeFile)
                                row = [str(datetime.now()),'no filepath, audio not saved' ,p[0,0], vol]
                                writer.writerow(row)

            except (KeyboardInterrupt, SystemExit):
                print('Shutting Down -- closing file')
                writer.close()
