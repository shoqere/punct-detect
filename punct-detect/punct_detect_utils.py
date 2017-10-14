from nltk import FreqDist
from collections import defaultdict
from collections import namedtuple
from itertools import product
import numpy as np

Sentence = namedtuple('Sentence',['words', 'puncts'])
Sentence_in_ID = namedtuple('Sentence_in_ID',['ids','p_ids'])

def indices_to_one_hot(data, nb_classes):
    """Convert an iterable of indices to one-hot encoded labels."""
    targets = np.array(data).reshape(-1)
    return np.eye(nb_classes)[targets]

def read_data(file, cutting_freq = 5,
              word_to_id=None, id_to_word = None,
              punct_to_id=None, id_to_punct=None):
	"""Return:
	data: an array of (sentence, puncts)
	id_to_word: an index-to-word dictionary of words in all sentences
	word_to_id: a word-to-index dictionary of words
	id_to_punct: an index-to-punctuation dictionary
	punct_to_id: an punctuation-to-id dictionary
	"""
	with open(file, encoding='utf-8') as fin:
		lines = fin.readlines()
		end_indexes = [i for (i, line) in enumerate(lines) if line == '\n']
		lines = [line.split() for line in lines]
		words = [line[0] if len(line) > 0 else None for line in lines]
		puncts = [line[1] if len(line) > 0 else None for line in lines]
		freq_dict = FreqDist(words)
		
		# Removing empty lines
		new_words = []
		new_puncts = []
		for i in range(len(words)):
			if words[i] == None or puncts[i] == None:
				continue
			new_words.append(words[i])
			new_puncts.append(puncts[i])
		
		words = new_words
		puncts = new_puncts
		
		# Creating index dictionary for words
		if word_to_id is None:
			word_to_id = defaultdict(lambda: 1)
			word_to_id['<PAD>'] = 0
			word_to_id['<UNK>'] = 1
			id_to_word = defaultdict(lambda: '<UNK>')
			id_to_word[0] = '<PAD>'
			most_common = freq_dict.most_common(len(freq_dict))
			order_list = [word for (word, freq) in most_common
			              if freq>cutting_freq]
			for i, word in enumerate(order_list):
				word_to_id[word] = i + 2
				id_to_word[i + 2] = word
				
		# Creating index dictionary for punctuations
		if punct_to_id is None:
			punct_to_id = {'<PAD>' : 0}
			punct_list = np.unique(puncts)
			id_to_punct = {0 : 'O'}
			i = 1
			for punct in punct_list:
				punct_to_id[punct] = i
				id_to_punct[i] = punct
				i+=1
			id_to_punct[punct_to_id['<PAD>']] = 'O'
		
		# # Padding
		data_words = []
		data_puncts = []
		max_length = 231
		start_index = 0
		# for end_index in end_indexes:
		# 	max_length = max(max_length,end_index-start_index+1)
		# 	start_index = end_index + 1
		#
		# start_index = 0
		# for end_index in end_indexes:
		# 	p = puncts[start_index: end_index]
		# 	w = words[start_index:end_index]
		# 	padding = max_length - (end_index-start_index+1)
		# 	if padding>0:
		# 		w = ['<PAD>'] * padding + w
		# 		p = ['<PAD>'] * padding + p
		# 	data_puncts = data_puncts + p
		# 	data_words = data_words + w
		# 	start_index = end_index + 1
		
		# Change into list of sentences
		data_puncts = defaultdict(lambda : []) # len -> array
		data_words = defaultdict(lambda : [])
		for end_index in end_indexes:
			p = puncts[start_index: end_index]
			w = words[start_index:end_index]
			if len(p)>0:
				data_puncts[len(p)].append(p)
				data_words[len(p)].append(w)
			start_index = end_index + 1
		return data_words, data_puncts, word_to_id, id_to_word, punct_to_id, id_to_punct, max_length


def process_data(words,puncts,word_to_id,punct_to_id):
	"""Change words and punctuations into indexes"""
	ids = defaultdict(lambda : [])
	p_ids = defaultdict(lambda : [])
	for l in words.keys():
		for i in range(len(words[l])):
			ids[l].append([word_to_id[w] for w in words[l][i]])
			p_ids[l].append([punct_to_id[p] for p in puncts[l][i]])
		
	return ids, p_ids


words, puncts, word_to_id, id_to_word, punct_to_id, id_to_punct, max1 = \
	read_data(r'../data/run/punc/punc.tr',5)
ids, p_ids = process_data(words,puncts,word_to_id,punct_to_id)

test_words, results, _ , _ , _, _, max2= \
	read_data(r'../data/run/punc/punc.ts',5,
	          word_to_id,id_to_word,punct_to_id,id_to_punct)
test_ids,test_p_ids = process_data(test_words,results,word_to_id,punct_to_id)
print(punct_to_id);
print(id_to_punct);
max_length = max(max1,max2)

from keras import backend as K


def weighted_categorical_crossentropy(weights):
	"""
	A weighted version of keras.objectives.categorical_crossentropy

	Variables:
		weights: numpy array of shape (C,) where C is the number of classes

	Usage:
		weights = np.array([0.5,2,10]) # Class one at 0.5, class 2 twice the normal weights, class 3 10x.
		loss = weighted_categorical_crossentropy(weights)
		model.compile(loss=loss,optimizer='adam')
	"""

	weights = K.variable(weights)

	def loss(y_true, y_pred):
		# scale predictions so that the class probas of each sample sum to 1
		y_pred /= K.sum(y_pred, axis=-1, keepdims=True)
		# clip to prevent NaN's and Inf's
		y_pred = K.clip(y_pred, K.epsilon(), 1 - K.epsilon())
		# calc
		loss = y_true * K.log(y_pred) * weights
		loss = -K.sum(loss, -1)
		return loss

	return loss

class WeightedCategoricalCrossEntropy(object):

  def __init__(self, weights):
    nb_cl = len(weights)
    self.weights = np.ones((nb_cl, nb_cl))
    for class_idx, class_weight in weights.items():
      self.weights[0][class_idx] = class_weight
      self.weights[class_idx][0] = class_weight
    self.__name__ = 'w_categorical_crossentropy'

  def __call__(self, y_true, y_pred):
    return self.w_categorical_crossentropy(y_true, y_pred)

  def w_categorical_crossentropy(self, y_true, y_pred):
    nb_cl = len(self.weights)
    final_mask = K.zeros_like(y_pred[..., 0])
    y_pred_max = K.max(y_pred, axis=-1)
    y_pred_max = K.expand_dims(y_pred_max, axis=-1)
    y_pred_max_mat = K.equal(y_pred, y_pred_max)
    for c_p, c_t in product(range(nb_cl), range(nb_cl)):
        w = K.cast(self.weights[c_t, c_p], K.floatx())
        y_p = K.cast(y_pred_max_mat[..., c_p], K.floatx())
        y_t = K.cast(y_pred_max_mat[..., c_t], K.floatx())
        final_mask += w * y_p * y_t
    return K.categorical_crossentropy(y_pred, y_true) * final_mask