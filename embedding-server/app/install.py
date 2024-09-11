from load_models import load_transformers, load_ner_models, load_toxic_models, load_jailbreak_models

print('installing transformers')
load_transformers()
print('installing ner models')
load_ner_models()
print('installing toxic models')
load_toxic_models()
print('installing jailbreak models')
load_jailbreak_models()