# -*- coding: utf-8 -*-
import scrapy
from util import logging_util
from bs4 import BeautifulSoup
from util import html_util
from rule_provider import rule_provider as rp
from properties import mapping as m
from text_processing_tools import post_processing_tool as ppt
from text_processing_tools import data_processing_tool as dpt
from repositories import Repository
from scrap_strategies import scraping_strategy_builder
from util.html_util import build_link
from filtering import filtering


class CategoriesSpider(scrapy.Spider):
    name = 'categories'
    repository = Repository.Repository()

    def __init__(self, start_url, scrap_mode, **kwargs):
        super().__init__(**kwargs)
        self.start_urls = [start_url]
        self.base_domain = start_url
        self.scrap_mode = scrap_mode
        self.logger_dbg = logging_util.get_logger("logs/debug")
        self.rule_provider = rp.RuleProvider()
        self.rule_provider.prepare_model()
        self.scraping_strategy = scraping_strategy_builder.get_strategy(scrap_mode)
        self.forum = self.scraping_strategy.init_strategy(self.base_domain)

    def parse(self, response):
        soup = BeautifulSoup(response.body, features="lxml")
        parent = response.meta.get('parent')
        for tag in self.rule_provider.possible_tags:
            elements_with_tag = soup.body.findAll(tag)
            for html_element in elements_with_tag:
                if html_util.element_has_css_class(html_element):
                    predicted = self.rule_provider.predict(tag, html_element["class"])
                    yield from self.scraping_strategy.execute_strategy(html_element, parent, predicted, tag, self.rule_provider, self)

    def parse_categories(self, html_element, predicted, parent):
        """
        Executes action of parsing the categories
        """
        category = None
        """ Title found"""
        if predicted == self.rule_provider.get_mapping(m.category_title):
            link = html_element['href']
            title = str(html_element.contents[0])
            category = self.repository.save_category(title, link, parent, self.forum)
            self.logger_dbg.info(title + " " + self.base_domain + link)

        """ Unwrapping needed """
        if predicted == self.rule_provider.get_mapping(m.category_whole):
            try:
                first_a_html_element_inside_whole = html_element.findAll("a")[0]
                link = first_a_html_element_inside_whole['href']
                title = str(first_a_html_element_inside_whole.contents[0])
                category = self.repository.save_category(title,link, parent, self.forum)
                self.logger_dbg.info(title + " " + self.base_domain + link)
            except BaseException as e:
                self.logger_dbg.error(str(e))
                self.logger_dbg.error("Can't find category inside: " + str(html_element))

        if category is not None and html_util.url_not_from_other_domain(category.link, self.base_domain):
            yield scrapy.Request(url=build_link(self.base_domain, category.link), callback=self.parse, meta={'parent': category})

    def parse_topics(self, html_element, parent):
        author = None
        date = None
        link = None
        title = None
        for tag in self.rule_provider.possible_tags_topics:
            elements_inside_tag = html_element.findAll(tag)
            for elem in elements_inside_tag:
                if html_util.element_has_css_class(elem):
                    predicted = self.rule_provider.predict(tag, elem["class"])
                    if predicted == self.rule_provider.get_mapping(m.topic_title):
                        title = elem.contents[0]
                        link = elem['href']
                        self.logger_dbg.info(title + " " + link)
                    if predicted == self.rule_provider.get_mapping(m.author):
                        author = elem.contents[0]
                    if predicted == self.rule_provider.get_mapping(m.topic_date):
                        date = dpt.parse_date(elem.contents)

        """ Additional check english speaking invision """
        time_tags = html_element.findAll("time")
        if len(time_tags) > 0:
            date = dpt.parse_english_date(time_tags[0].contents)
            link =  html_element.findAll('a')[0]['href']
            title = html_element.findAll('a')[0]['title']

        if title is None or link is None:
            self.logger_dbg.info("Can't find topic inside: " + str(html_element))
            return

        if not filtering.topic_meets_criterion(title, author, date):
            return
        topic = self.repository.save_topic(author, date, link, parent, title)
        self.logger_dbg.info("Scrapped topic: " + str(topic))
        yield scrapy.Request(dont_filter=True, url=build_link(self.base_domain, topic.link), callback=self.parse,
                             meta={'parent': topic})

    def parse_posts(self, html_element, parent):
        """
        Executes action of parsing the post
        """
        self.logger_dbg.info("Parsing post of topic: " + parent.title)
        author = None
        date = None
        content = None
        """Go through all the possible tags that occur in posts and determine their function """
        for tag in self.rule_provider.possible_tags_posts:
            elements_with_tag = html_element.findAll(tag)
            for elem in elements_with_tag:
                if html_util.element_has_css_class(elem):
                    predicted = self.rule_provider.predict(tag, elem["class"])
                    if predicted == self.rule_provider.get_mapping(m.post_body):
                        content = filtering.assign_new_value_if_changed_and_not_null(content, ppt.contents_to_plain_text(elem.contents))
                    if predicted == self.rule_provider.get_mapping(m.author):
                        author = elem.contents[0]
                    if predicted == self.rule_provider.get_mapping(m.post_date):
                        date = dpt.parse_date(elem.contents)
        """Perform additional check for english format of date """
        time_tags = html_element.findAll("time")
        if len(time_tags) > 0 and date is None:
            date = dpt.parse_english_date(time_tags[0].contents)
        if content is not None and filtering.post_meets_criterions(content, author, date):
            self.repository.save_post(author, content, date, parent)

    def go_to_next_page(self, html_element, parent, predicted):
        """
        Executes action of going to the next page
        """
        if predicted == self.rule_provider.get_mapping(m.next_page):
            try:
                first_a_html_element_inside_whole = html_element.findAll("a")[0]
                link = first_a_html_element_inside_whole['href']
                self.logger_dbg.info("Going to next page: " + str(parent) + " unwrapped url: " + link)
                yield scrapy.Request(url=build_link(self.base_domain, link), callback=self.parse,
                                     meta={'parent': parent})
            except BaseException as e:
                self.logger_dbg.error("Couldn't go to next page of: " + str(parent) + " due to: " + str(e))
                self.logger_dbg.error("Element that caused the problem: " + str(html_element))
        elif predicted == self.rule_provider.get_mapping(m.next_page_link):
            self.logger_dbg.info("Going to next page: " + str(parent) + " url: " + html_element['href'])
            yield scrapy.Request(url= build_link(self.base_domain, html_element['href']), callback=self.parse,
                                 meta={'parent': parent})

    def closed(self, reason):
        self.scraping_strategy.finish_strategy()
