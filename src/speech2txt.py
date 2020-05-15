import os
import time
from pathlib import Path
import sys
import logging

if not os.path.isdir('../logs'):
    os.makedirs('../logs')
with open('../logs/speech2txt.log', 'w'):
    pass
log_speech = logging.getLogger(__name__)
log_speech.setLevel(logging.INFO)
handler_f = logging.FileHandler('../logs/speech2txt.log')
handler_f.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s'))
log_speech.addHandler(handler_f)

#try:
import utils
from audio import record_audio
from nn import model, predict
#except ImportError as e:
#    log_speech.warning("might be missing speech recognition modules required for --speech only")
#    log_speech.warning("clone from https://github.com/SASVDERDBGTYS/SpeechRecog.git")
#    log_speech.error(str(e))

def speech2txt(buff, trigger):
    resource_path = Path(os.getcwd()) / 'resources'
    duration = 2
    fs = 16000
    nsample = duration * fs
    nclass = 2

    try:
        trigger.set()
        with utils.suppress_stdout():
            log_speech.info("loading speech2txt model")
            m = model.full_model(fs, nsample, nclass=nclass, n_hop=128, load_model=True, resource_path=resource_path)
        while trigger.wait():
            log_speech.info("speech prediction is triggered")
            print("choose right or left after the beep")
            time.sleep(1)
            audio = record_audio.record(duration, fs, resource_path)
            pred = 'r' if predict.predict(m, audio) else 'l'
            buff.put(pred, block=True)
            log_speech.info('model predicted %s' %pred)
            trigger.clear()
    except TypeError as e:
        log_speech.error('Failed to import utils, audio, or nn')
        log_speech.error(str(e))
    except KeyboardInterrupt as e:
        log_speech.info("Forcebly closed by user: %s" %str(e))