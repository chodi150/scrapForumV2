import pandas as pd
import nltk
import re
from nltk.corpus import stopwords
import hunspell
from sklearn.feature_extraction.text import TfidfVectorizer
from glove import Corpus, Glove
from preprocessing_text_data.preprocessing import correct_writing, build_post_repr
import numpy as np

from repositories import Repository


def swap(word, swap_rule):
    return word.replace(swap_rule[0], swap_rule[1])


def prepare(forum_id, date_from, date_to, filename):
    repository = Repository.Repository()
    data = repository.get_posts(date_from, date_to, forum_id)
    data_frame = pd.DataFrame(data, columns=['post', 'post_date', 'topic_title', 'category'])
    data_frame.post = data_frame.post.apply(lambda x: re.sub(' ?(f|ht)tp(s?)://(.*)[0-9][.][a-z]+', '', x))
    data_frame.post = data_frame.post.apply(lambda x: str.lower(x))
    data_frame.post = data_frame.post.apply(lambda x: re.sub(r'[^\w\s]', ' ', x))
    data_frame.post = data_frame.post.apply(lambda x: re.sub(r'\d+', ' ', x))
    tokens = data_frame.post.apply(lambda x: nltk.word_tokenize(x))
    hun = hunspell.Hunspell('pl')
    counter = [0]
    tokens_stemmed = tokens.apply(lambda x: correct_writing(hun, x, counter))
    stops = set(stopwords.words('polish'))
    tokens_stemmed = tokens_stemmed.apply(lambda x: [item for item in x if item not in stops])
    data_frame.post = tokens_stemmed
    data_frame.to_csv(filename, sep=';', escapechar='\\')
    return data_frame


def do_tfidf(forum_id, date_from, date_to, filename, max_df,min_df):
    data_frame = prepare(forum_id, date_from,date_to, "prepare_" + filename)
    data_frame.post = data_frame.post.apply(lambda x: " ".join(x))
    data_frame.post = data_frame.post.apply(lambda x: re.sub(r'[^\w\s]', '', x))
    stops = set(stopwords.words('polish'))
    vectorizer = TfidfVectorizer(stop_words=stops, min_df=min_df, max_df=max_df)
    vectorizer.fit(data_frame.post)
    tfidf = pd.DataFrame(vectorizer.transform(data_frame.post).toarray(), columns=vectorizer.get_feature_names())
    tfidf['category'] = data_frame.category
    only_nulls = list(map(lambda x: np.all(x[0:len(x)-1]==0), tfidf.values))
    tfidf['only_nulls'] = np.array(only_nulls)
    tfidf = tfidf[tfidf['only_nulls'] == False]
    tfidf = tfidf.drop('only_nulls', axis=1)
    filename = "dict_size_" + str(len(vectorizer.get_feature_names())) + "_" + filename

    tfidf.to_csv(filename, sep=';', escapechar='\\', encoding='utf-8')


def do_glove(forum_id, date_from,date_to, filename, window_size, vec_dim, max_df,min_df):
    data_frame = prepare(forum_id, date_from, date_to, "prepare_" + filename)
    data_frame.post = data_frame.post.apply(lambda x: " ".join(x))
    stops = set(stopwords.words('polish'))
    vectorizer = TfidfVectorizer(stop_words=stops, min_df=min_df, max_df=max_df, use_idf=False)
    vectorizer.fit(data_frame.post)
    data_frame.post = data_frame.post.apply(lambda x: x.split(" "))
    corpus = Corpus(vectorizer.vocabulary_)
    corpus.fit(data_frame.post, window=window_size, ignore_missing=True)
    glove = Glove(no_components=vec_dim, learning_rate=0.01)
    glove.fit(corpus.matrix, epochs=1, no_threads=4, verbose=True)
    glove.add_dictionary(corpus.dictionary)
    pd.DataFrame(glove.word_vectors).to_csv("word_vectors" + filename, sep=';')

    representations = pd.DataFrame()
    for post in data_frame.post:
        representations = representations.append(build_post_repr(post, glove))
    representations['belongs_to'] = data_frame.category.values
    representations = representations[representations['delete'] == False]
    representations = representations.drop('delete', axis=1)
    representations.to_csv(filename, sep=';')
