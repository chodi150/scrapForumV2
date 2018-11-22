import pandas as pd
from sklearn import tree
import numpy as np
from util import forum_elements_mapper as fem

class RuleProvider:

    def __init__(self):
        self.rules = None
        self.classifier = None
        self.possible_tags = None
        self.possible_classes = None
        self.mapper = fem.ForumElementsMapper()

    def initialize_rules(self):
        self.rules = pd.read_csv("config/rules.csv", sep=';', header=None, names = ['tag', 'class', 'value'])
        self.possible_tags = set(self.rules['tag'])
        self.possible_classes = set(self.rules['class'])
        self.mapper.initialize_tag_mapper(np.array(self.rules['tag']))
        self.mapper.initialize_class_mapper(np.array(self.rules['class']))
        self.rules['value'] = self.rules['value'].map(lambda a: self.mapper.mappings[a])
        self.rules['tag'] = self.rules['tag'].map(lambda a: self.mapper.tags[a])
        self.rules['class'] = self.rules['class'].map(lambda a: self.mapper.classes[a])

    def prepare_model(self):
        self.initialize_rules()
        self.classifier = tree.DecisionTreeClassifier()
        np_rules = np.array(self.rules)
        self.classifier.fit = self.classifier.fit(np_rules[:,0:2], np_rules[:,2])

    def predict(self, tag, classes):
        classes_as_string = " ".join(classes)

        if classes_as_string not in self.possible_classes:
            return 12
        return self.classifier.predict([[self.mapper.tags[tag], self.mapper.classes[classes_as_string]]])

