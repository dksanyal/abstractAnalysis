from nltk.tokenize import TweetTokenizer
from gensim.models import KeyedVectors
from sklearn.metrics import confusion_matrix, accuracy_score, recall_score, precision_score, f1_score
from keras_contrib.layers import CRF
from keras.preprocessing.sequence import pad_sequences
from keras.layers import Dense, Input, Lambda, merge, dot, Subtract, Flatten, LSTM, BatchNormalization
from keras.layers.embeddings import Embedding
from keras.layers.recurrent import GRU
from keras.layers.core import Dropout, Activation, Reshape
from keras.layers.wrappers import Bidirectional, TimeDistributed
from keras.layers.merge import Concatenate, Add, Multiply
from keras.utils import plot_model, to_categorical
from keras.models import Model, model_from_json, load_model
from keras.callbacks import TensorBoard, EarlyStopping, ModelCheckpoint
import keras.backend as K
import numpy as np
import collections, os, re, traceback, pickle, pdb
#!import code; code.interact(local=vars())

from spacy.lang.en import English

def format_abstract(abstract):
	nlp         	= English()
	sentencizer 	= nlp.create_pipe("sentencizer")
	nlp.add_pipe(sentencizer)


	raw_data 			= []    
	structured_data 	= [] 
	structured_labels 	= []
	buffered_abstract 	= []  
	buffered_labels 	= [] 
	

	for sentence in nlp(abstract).sents:
		line = sentence.strip()                                      
		raw_data.append(line) # The original traning data  					

		if line:                          
			data = tt.tokenize(line)			
			data =  data[1:] 
			data = [word.lower() for word in data if word.isalnum()]

			if len(data)<=3:
				try:
					buffered_abstract[-1]+=data # append to previous line					
				except Exception as e:
					buffered_abstract.append(data)
			else:
				buffered_abstract.append(data) 


	if buffered_abstract:
		structured_data.append(buffered_abstract)



	X 		= []
	X_words = []


	for abstract in structured_data:
		indexed_abstract 		= []
		indexed_abstract_word 	= []
		for sentence in abstract:
			indexed_sentence 		= []
			indexed_word_sentence 	= []
			for word in sentence:
				try:
					index = word2idx[word]
				except:
					index = -1
				indexed_sentence.append(index)
				indexed_word = []
				for char in word:
					try:
						char_index = char2idx[char]
					except:
						char_index = -1
					indexed_word.append(char_index)
				indexed_word_sentence.append(indexed_word)
			# padding or pruning indexed_word_sentence as per nessacity
			indexed_word_sentence = pad_sequences(indexed_word_sentence, maxlen=maxlen_word)
			indexed_abstract.append(indexed_sentence)
			indexed_abstract_word.append(indexed_word_sentence)

		indexed_abstract  		= pad_sequences(indexed_abstract , maxlen=maxlen)
		indexed_abstract_word  	= pad_sequences(indexed_abstract_word , maxlen=maxlen)
		X.append(indexed_abstract)
		X_words.append(indexed_abstract_word)


	
	X =  pad_sequences(X, abs_len,padding='post', value=0)
	X_words =  pad_sequences(X_words, abs_len, padding='post', value=0)
	# pdb.set_trace()
	return X, X_words



# abstract = "With the smart grid (SG) and the social Internet of Things (SIoT), an electric vehicle operator can use reliable, flexible, and efficient charging service with vehicle-to-grid (V2G). However, open channels can be vulnerable to various attacks by a malicious adversary. Therefore, secure mutual authentication for V2G has become essential, and numerous related protocols have been proposed. In 2018, Shen et al. proposed a privacy-preserving and lightweight key agreement protocol for V2G in SIoT to ensure security. However, we demonstrate that their protocol does not withstand impersonation, privileged-insider, and offline password guessing attacks, and it does not also guarantee secure mutual authentication, session key security, and perfect forward secrecy. Therefore, this paper proposes a dynamic privacy-preserving and lightweight key agreement protocol for V2G in SIoT to resolve the security weaknesses of Shen et al.'s protocol. The proposed protocol resists several attacks including impersonation, offline password guessing, man-in-the-middle, replay, and trace attacks, ensures anonymity, perfect forward secrecy, session key security, and secure mutual authentication. We evaluate the security of the proposed protocol using formal security analysis under the broadly-accepted real-or-random (ROR) model, secure mutual authentication proof using the widely-accepted Burrows-Abadi-Needham (BAN) logic, informal (non-mathematical) security analysis, and also the formal security verification using the broadly-accepted automated validation of Internet security protocols and applications (AVISPA) tool. We then compare computation costs, and security and functionality features of the proposed protocol with related protocols. Overall, the proposed protocol provides superior security, and it can be efficiently deployed to practical SIoT-based V2G environment."



def label_transform(label):
 switcher = { 
     u'BACKGROUND'	: u'BACKGROUND+OBJECTIVE', 
     u'OBJECTIVE'	: u'BACKGROUND+OBJECTIVE', 
     u'METHODS'		: u'METHODS',
     u'RESULTS'		: u'RESULTS+CONCLUSIONS',  
     u'CONCLUSIONS'	: u'RESULTS+CONCLUSIONS',
 }
 return switcher.get(label, u'UNDEFINED')  

def get_data_dicts(structured_data, abs_len=30, maxlen = 130, maxlen_word = 25):
	words   	= set()
	charcounts 	= collections.Counter()
	for abstract in structured_data:
		sent_len = 0
		for sentence in abstract:
			word_len = 0
			sent_len += 1
			for word in sentence:
				words.add(word)				
				word_len +=1
				char_len = 0
				for char in word:
					charcounts[char] += 1
					char_len +=1
				if maxlen_word < char_len:
					maxlen_word = char_len
			if maxlen < word_len:
					maxlen = word_len
		if abs_len < sent_len:
			abs_len = sent_len
	
	words   = list(words)
	 #for converting words to indices
	word2idx    = {w: i+1 for i, w in enumerate(words)}
	chars 		= [charcount[0] for charcount in charcounts.most_common()]
	char2idx 	= {c: i+1 for i, c in enumerate(chars)}

	# for converting indices back to words
	idx2word    = dict((k,v) for v,k in word2idx.items())
	
	idx2word[0]     = 'PAD'
	idx2word[-1]    = 'unknown'

	vocsize =  len(words)+1


	# check nessacituy
	idx2char  = dict((k,v) for v,k in char2idx.items())
	idx2char[0] = 'PAD'
	charsize =  max(idx2char.keys()) + 1


	return idx2word,  word2idx, char2idx, abs_len, maxlen, maxlen_word, vocsize, charsize

def get_final_data(structured_data, structured_labels, data_dicts):
	#Defaults : abs_len =30, maxlen=130, maxlen_word = 25
	(idx2word,  word2idx, char2idx, label2idx, abs_len, maxlen, maxlen_word, vocsize, charsize, nclasses) = data_dicts
	X 		= []
	X_words = []
	Y 		= []

	for abstract in structured_data:
		indexed_abstract 		= []
		indexed_abstract_word 	= []
		for sentence in abstract:
			indexed_sentence 		= []
			indexed_word_sentence 	= []
			for word in sentence:
				try:
					index = word2idx[word]
				except:
					index = -1
				indexed_sentence.append(index)
				indexed_word = []
				for char in word:
					try:
						char_index = char2idx[char]
					except:
						char_index = -1
					indexed_word.append(char_index)
				indexed_word_sentence.append(indexed_word)
			# padding or pruning indexed_word_sentence as per nessacity
			indexed_word_sentence = pad_sequences(indexed_word_sentence, maxlen=maxlen_word)
			indexed_abstract.append(indexed_sentence)
			indexed_abstract_word.append(indexed_word_sentence)

		indexed_abstract  		= pad_sequences(indexed_abstract , maxlen=maxlen)
		indexed_abstract_word  	= pad_sequences(indexed_abstract_word , maxlen=maxlen)
		X.append(indexed_abstract)
		X_words.append(indexed_abstract_word)


	for labels in structured_labels:
		indexed_labels = []
		for label in labels:
			indexed_labels.append(label2idx[label]) 


		Y.append(indexed_labels)


	X =  pad_sequences(X, abs_len,padding='post', value=0)
	X_words =  pad_sequences(X_words, abs_len, padding='post', value=0)
	Y =  pad_sequences(Y, abs_len, padding='post', value=0)
	Y = to_categorical(Y)
	# pdb.set_trace()
	return X, X_words, Y 

def get_data(abstract, data_dicts):
	# defauls : abs_len =30, maxlen=130, maxlen_word = 25
	#  data_path = 'data/pubmed_non_rct.txt'
	input_data = list(open(data_path, 'r'))

	tt = TweetTokenizer()
	labels = [u'BACKGROUND', u'OBJECTIVE', u'METHODS', u'RESULTS',  u'CONCLUSIONS']
	#  evantual shape labels = [u'BACKGROUND+OBJECTIVE', u'METHODS', u'RESULTS+CONCLUSIONS']
	raw_data 			= []    
	structured_data 	= [] 
	structured_labels 	= []
	buffered_abstract 	= []  
	buffered_labels 	= []  

	for line in input_data:
			line = line.strip()                                      
			raw_data.append(line) # The original traning data         

			if line.startswith('###'):#, 0,len(line)):
				if buffered_abstract:
					structured_data.append(buffered_abstract)	
					structured_labels.append(buffered_labels)
					buffered_abstract 	= []  
					buffered_labels 	= [] 					

			else:					
				if line:                          
					data = tt.tokenize(line)
					label = data[0]
					data =  data[1:] 
					data = [word.lower() for word in data if word.isalnum()]

					if label in labels:

						if conv_to_3_class:
							label = label_transform(label)	

						if len(data)<=3:
							try:
								if label == buffered_labels[-1]:
									buffered_abstract[-1]+=data # append to previous line
									#label is same
								else : 
									# skip this line
									pass 
							except Exception as e:
								# skip this line
								pass 
						else:
							buffered_abstract.append(data) 
							buffered_labels.append(label)
	if conv_to_3_class: 							   
		labels = list(set([label_transform(label) for label in labels]))

										   
	if data_dicts is not None:
		(idx2word,  word2idx, char2idx, label2idx, abs_len, maxlen, maxlen_word, vocsize, charsize, nclasses) = data_dicts
		# (word2idx, char2idx, label2idx, idx2word, maxlen, maxlen_word) = data_dicts
	else:
		idx2word,  word2idx, char2idx, abs_len, maxlen, maxlen_word, vocsize, charsize = get_data_dicts(structured_data)
		label2idx   = {l: i+1 for i, l in enumerate(labels)}
		nclasses = len(labels)+1 # 0;  for pad lines
		data_dicts = (idx2word,  word2idx, char2idx, label2idx, abs_len, maxlen, maxlen_word, vocsize, charsize, nclasses)


	X, X_words, Y = get_final_data(structured_data, structured_labels, data_dicts)			
	
	# except Exception as e:
	# 	traceback.print_exc()
	# 	pdb.set_trace() 

	# if data_dicts is None:
	# 	data_dicts = (idx2word,  word2idx, label2idx, maxlen, maxlen_word, vocsize, charsize, nclasses)
	# else:
	# 	data_dicts = None

	# pdb.set_trace() 
		
	return X, X_words, Y, data_dicts

def data_fetch(embed_top_n = -1, conv_to_3_class = True):
				
	data_path_train='/users/debarshi/soumya/PubMedData/output/train_clean.txt' 
	data_path_val = '/users/debarshi/soumya/PubMedData/output/dev_clean.txt'
	data_path_test = '/users/debarshi/soumya/PubMedData/output/test_clean.txt'
	w2v_glove_300d_path = '/users/debarshi/soumya/abstractAnalysis/ANMLAD/pubmed_adr/word2vec_format_glove.42B.300d.txt'
	embed_dim = 300
	char_embed_dim = 100				
				

	X_train , X_train_words, Y_train, data_dicts  	= get_data(data_path_train, None, conv_to_3_class)
	X_test, X_test_words, Y_test, _ 				= get_data(data_path_test, data_dicts, conv_to_3_class)
	X_val, X_val_words, Y_val, _ 					= get_data(data_path_val, data_dicts, conv_to_3_class)
	
	# 	pdb.set_trace() 	

	print('Loading word embeddings...')
	if embed_top_n == -1:
		w2v = KeyedVectors.load_word2vec_format(w2v_glove_300d_path, binary=False, unicode_errors='ignore')
	else:
		w2v = KeyedVectors.load_word2vec_format(w2v_glove_300d_path, binary=False, unicode_errors='ignore', limit=embed_top_n)
	# w2v = KeyedVectors.load_word2vec_format(glove_300d_path, binary=False, unicode_errors='ignore')
	print('word embeddings loading done!')

	train 		= (X_train, X_train_words, Y_train)
	val  		= (X_val, X_val_words, Y_val)
	test 		= (X_test, X_test_words, Y_test)
	enbed_data 	= (w2v , embed_dim, char_embed_dim)

	return data_dicts, train, val, test, enbed_data

def get_abstract(idx2word, X_i):
	abstract = []
	for line in X_i:
		line_content = ''
		for idx in line:
			word = idx2word[idx]
			if idx != 0:
				line_content += word+' '
		if line_content:
			abstract.append(line_content)
	return abstract

def get_labels(label2idx, Y_i):
	idx2label =  dict((k,v) for v,k in label2idx.items())
	return [idx2label[i] for i in Y_i] 



def save_dictionaries(data_dicts, enbed_data, suffix):
	print('Saving data dictionaries...')
	serialized = pickle.dumps([data_dicts, enbed_data])
	with open('saved_model/model_dict'+suffix+'.pkl', 'wb') as f:  # Python 3: open(..., 'wb')
		f.write(serialized)

def load_dictionaries(suffix):
	try:
		with open('saved_model/model_dict'+suffix+'.pkl', 'rb') as f:  # Python 3: open(..., 'wb')
			raw = f.read()
		[data_dicts, enbed_data] = pickle.loads(raw) 
		return data_dicts, enbed_data
	except Exception as e:
		return None
	

def save_model_weight(model, sufix):
	# serialize model to JSON
	# model_json = model.to_json()
	# with open("saved_model/model.json", "w") as json_file:
	#     json_file.write(model_json)
	# serialize weights to HDF5
	model.save_weights("saved_model/model_weights"+sufix+".h5")
	print("Saved model weights to disk")
	# model.save("saved_model/model.h5")
	# print("Saved model to disk.")

def load_model_weight(model, sufix):
	try:
		# son_file = open('saved_model/model.json', 'r')
		# loaded_model_json = json_file.read()
		# json_file.close()
		# loaded_model = model_from_json(loaded_model_json)
		# load weights into new model
		from pathlib import Path
		saved_model = Path("saved_model/model_weights"+sufix+".h5")
		if saved_model.is_file():
			model.load_weights("saved_model/model_weights"+sufix+".h5")
			print("Loaded model weights from disk")
			# model = load_model(saved_model)
			# print("Loaded model from disk.")
			return model
		else :
			print("Saved weights not found.")
	except Exception as e:
		print("Saved weights incompatable.")
		# traceback.print_exc()
		# pdb.set_trace() 

		return None

def get_results(pred, gold):
	non_pad_pred 	= []
	non_pad_gold	= []
	for (i,abstract) in enumerate(gold):
		 for (j,label) in enumerate(abstract):
		 	g_l = np.argmax(label)  
		 	if g_l != 0:
		 		p_l = np.argmax(pred[i,j])
		 		non_pad_pred.append(p_l)
		 		non_pad_gold.append(g_l)
	CM 	= confusion_matrix(non_pad_gold, non_pad_pred)
	acc = accuracy_score(non_pad_gold, non_pad_pred)

	return acc, CM, non_pad_pred, non_pad_gold

def main(absract, sufix=''):
	# Definition of some parameters
	try:
		data_dicts, enbed_data  = load_dictionaries(sufix)		
		save_file_sufix 		= sufix		
		model 					= model_basic(data_dicts, enbed_data)

		if load_model_weight_from_disk:
			model_weights = load_model_weight(model, save_file_sufix)
			if model_weights  is not None:
				model = model_weights

		pred_probs = model.predict([X_test, X_test_words], verbose=0)
		acc, CM, pred, gold = get_results(pred_probs, Y_test)



		print ('Accuracy :'+ str(acc) +'\n Confusion_matrix : \n')

		print (CM)
		
		pdb.set_trace() 

		# print 'passed checkpoint 10: prediction\n\n'
		# plot_model(model, to_file='model.png', show_shapes=True)

	except Exception as e:
		# print 'passed checkpoint E1\n\n'
		# model.summary()
		# plot_model(model, to_file='model.png', show_shapes=True)

		traceback.print_exc()
		pdb.set_trace() 



# import sys
# args = sys.argv

# try:
# 	num_epoch =  int(args[1])
# except Exception as e:
# 	num_epoch 	= 10
# try:
# 	embed_top_n =  int(args[2])
# except Exception as e:
# 	embed_top_n 	= -1 # all
# try:
# 	load_model_weight_from_disk =  Bool(args[3])
# except Exception as e:
# 	load_model_weight_from_disk 	= True
# try:
# 	save_model_weight_to_disk =  Bool(args[4])
# except Exception as e:
# 	save_model_weight_to_disk 	= True



# if __name__== "__main__":
# 	# main(load_model_weight_from_disk= True, save_model_weight_to_disk=True, embed_top_n =  None):
# 	main(num_epoch, embed_top_n, load_model_weight_from_disk, save_model_weight_to_disk)