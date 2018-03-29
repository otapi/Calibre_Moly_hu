#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
						print_function)

__license__   = 'GPL v3'
__copyright__ = '2011-2014, Hoffer Csaba <csaba.hoffer@gmail.com>, Kloon <kloon@techgeek.co.in>'
__docformat__ = 'restructuredtext hu'

import socket, re, datetime
from threading import Thread
from lxml.html import fromstring
from calibre.ebooks.metadata.book.base import Metadata
import lxml, sys
import lxml.html as lh
from calibre.utils.date import utcnow
from datetime import datetime
from dateutil import parser
from calibre.ebooks.metadata import MetaInformation
from calibre.utils.cleantext import clean_ascii_chars
from calibre import browser

class Worker(Thread): # Get details
	'''
	Get book details from moly.hu book page in a separate thread
	'''

	def __init__(self, url, result_queue, browser, log, relevance, plugin, timeout=30):
		Thread.__init__(self)
		self.daemon = True
		self.url, self.result_queue = url, result_queue
		self.log, self.timeout = log, timeout
		self.relevance, self.plugin = relevance, plugin
		self.browser = browser.clone_browser()
		self.max_covers = plugin.prefs[plugin.KEY_MAX_COVERS]
		self.cover_url = self.moly_id = self.isbn = None

	def run(self):
		try:
			self.get_details()
		except:
			self.log.exception('get_details failed for url: %r'%self.url)

	def get_details(self):
		try:
			raw = self.browser.open_novisit(self.url, timeout=self.timeout).read().strip()
			raw = raw.decode('utf-8', errors='replace')
			if not raw:
				log.error('Failed to get raw result for query: %r'%query)
				return
		except Exception as e:
			if callable(getattr(e, 'getcode', None)) and e.getcode() == 404:
				self.log.error('URL malformed: %r'%self.url)
				return
			attr = getattr(e, 'args', [None])
			attr = attr if attr else [None]
			if isinstance(attr[0], socket.timeout):
				msg = 'Moly.hu timed out. Try again later.'
				self.log.error(msg)
			else:
				msg = 'Failed to make details query: %r'%self.url
				self.log.exception(msg)
			return

		root = fromstring(clean_ascii_chars(raw))
		self.parse_details(root)

	def parse_details(self, root):
		try:
			moly_id = self.parse_moly_id(self.url)
			self.log.info('Parsed moly.hu identifier: %s'%moly_id)
		except:
			self.log.exception('Error parsing moly.hu id for url: %r'%self.url)
			moly_id = None

		try:
			title = self.parse_title(root)
			self.log.info('Parsed title: %s'%title)
		except:
			self.log.exception('Error parsing title for url: %r'%self.url)
			title = None
		
		try:
			authors = self.parse_authors(root)
			self.log.info('Parsed authors: %s'%authors)
		except:
			self.log.exception('Error parsing authors for url: %r'%self.url)
			authors = []

		if not title or not authors or not moly_id:
			self.log.error('Could not find title/authors/moly.hu id for %r'%self.url)
			self.log.error('Moly.hu id: %r Title: %r Authors: %r'%(moly_id, title, authors))
			return

		mi = Metadata(title, authors)
		mi.set_identifier('moly_hu', moly_id)
		self.moly_id = moly_id

		try:
			isbn = self.parse_isbn(root)
			self.log.info('Parsed ISBN: %s'%isbn)
			if isbn:
				self.isbn = mi.isbn = isbn
		except:
			self.log.exception('Error parsing ISBN for url: %r'%self.url)
		
		try:
			series_info = self.parse_series(root)
			if series_info is not None:
				mi.series = series_info[0]
				mi.series_index = int(series_info[1])
				self.log.info('Parsed series: %s, series index: %f'%(mi.series,mi.series_index))
		except:
			self.log.exception('Error parsing series for url: %r'%self.url)
			
		try:
			mi.comments = self.parse_comments(root)
			self.log.info('Parsed comments: %s'%mi.comments)
		except:
			self.log.exception('Error parsing comments for url: %r'%self.url)

		try:
			self.cover_url = self.parse_covers(root)
			self.log.info('Parsed URL for cover: %r'%self.cover_url)
			self.plugin.cache_identifier_to_cover_url(self.moly_id, self.cover_url)
			mi.has_cover = bool(self.cover_url)
		except:
			self.log.exception('Error parsing cover for url: %r'%self.url)

		try:
			mi.tags = self.parse_tags(root)
			self.log.info('Parsed tags: %s'%mi.tags)
		except:
			self.log.exception('Error parsing tags for url: %r'%self.url)
			
		try:
			mi.languages = self.parse_languages(mi.tags)
			self.log.info('Parsed languages: %r'%mi.languages)
		except:
			self.log.exception('Error parsing language for url: %r'%self.url)
			
		try:
			mi.publisher = self.parse_publisher(root)
			self.log.info('Parsed publisher: %s'%mi.publisher)
		except:
			self.log.exception('Error parsing publisher for url: %r'%self.url)	
			
		try:
			mi.pubdate = self.parse_published_date(root)
			self.log.info('Parsed publication date: %s'%mi.pubdate)
		except:
			self.log.exception('Error parsing published date for url: %r'%self.url)
			
		try:
			mi.rating = self.parse_rating(root)
			self.log.info('Parsed rating: %s\n\n'%mi.rating)
		except:
			self.log.exception('Error parsing tags for url: %r\n\n'%self.url)


		mi.source_relevance = self.relevance

		if self.moly_id and self.isbn:
			self.plugin.cache_isbn_to_identifier(self.isbn, self.moly_id)

		self.plugin.clean_downloaded_metadata(mi)

		self.result_queue.put(mi)

	def parse_moly_id(self, url):
		try:
			m = re.search('/konyvek/(.*)', url)
			if m:
				return m.group(1)
		except:
			return None
		
	def parse_isbn(self, root):
		isbn = None
		isbn_node = root.xpath('//*[@id="content"]//*[@class="items"]/div/div[2]/text()')
		for isbn_value in isbn_node:
			m = re.search('(\d{13}|\d{10})', isbn_value)
			if m:
				isbn = m.group(1)
				break
		
		return isbn
		
	def parse_title(self, root):
		title_node = root.xpath('//*[@id="content"]//*[@class="fn"]/text()')
		self.log.info('Title: %s'%title_node)
		if title_node:
			return title_node[0].strip()
			
	def parse_series(self, root):
		series_node = root.xpath('//*[@id="content"]//*[@class="fn"]/a/text()')
		if not series_node:
			return None
		
		return series_node[0].strip('().').rsplit(' ', 1)
		
	def parse_authors(self, root):
		author_nodes = root.xpath('//*[@id="content"]//div[@class="authors"]/a/text()')
		self.log.info('Authors: %r'%author_nodes)
		if author_nodes:
			return [unicode(author) for author in author_nodes]

	def parse_tags(self, root):
		tags_node = root.xpath('//*[@id="tags"]//*[@class="hover_link"]/text()')
		tags_node = [unicode(text) for text in tags_node if text.strip()]
		if tags_node:
			return tags_node
			
	def parse_comments(self, root):
		description_node = root.xpath('//*[@id="content"]//*[@class="text" and @id="full_description"]/p/text()')
		if not description_node:
			description_node = root.xpath('//*[@id="content"]//*[@class="text"]/p/text()')
		
		if description_node:
			return '\n'.join(description_node)
			
	def parse_publisher(self, root):
		publisher_node = root.xpath('//*[@id="content"]//*[@class="items"]/div/div[1]/a/text()')
		if publisher_node:
			return publisher_node[0]
		
	def parse_published_date(self, root):
		pub_year = None
		publication_node = root.xpath('//*[@id="content"]//*[@class="items"]/div/div[1]/text()')
		for publication_value in publication_node:
			m = re.search('(\d{4})', publication_value)
			if m:
				pub_year = m.group(1)
				break
		
		if not pub_year:
			return None
		default = datetime.utcnow()
		from calibre.utils.date import utc_tz
		default = datetime(default.year, default.month, default.day, tzinfo=utc_tz)
		pub_date = parser.parse(pub_year, default=default)
		if pub_date:
			return pub_date
	
	def parse_rating(self, root):
		rating_node = root.xpath('//*[@id="content"]//*[@class="rating"]//*[@class="like_count"]/text()')
		#rating_node = round(float(rating_node[0].strip().strip('%'))*0.05)
		if rating_node:
			return round(float(rating_node[0].strip('%').strip())*0.05)
	
	def parse_covers(self, root):
		from calibre_plugins.moly_hu import Moly_hu
		book_covers = root.xpath('(//*[@class="coverbox"]//a/@href)[position()<=%d]'%self.max_covers)
		if book_covers:
			return [Moly_hu.BASE_URL + cover_url for cover_url in book_covers]
	
	def parse_languages(self, tags):
		langs = []
		for tag in tags:
			langId = self._translateLanguageToCode(tag)
			if langId is not None:
				langs.append(langId)
		
		if not langs:
			return ['hu']
		
		return langs
	
	def _translateLanguageToCode(self, displayLang):
		displayLang = displayLang.lower().strip() if displayLang else None
		langTbl = { None: 'und', 
					u'angol nyelv\u0171': 'en',
					u'n\xe9met nyelv\u0171': 'de',
					u'francia nyelv\u0171': 'fr',
					u'olasz nyelv\u0171': 'it', 
					u'spanyol nyelv\u0171': 'es',
					u'orosz nyelv\u0171': 'ru',
					u't\xf6r\xf6k nyelv\u0171': 'tr',
					u'g\xf6r\xf6g nyelv\u0171': 'gr',
					u'k\xednai nyelv\u0171': 'cn',
					u'jap\xe1n nyelv\u0171': 'jp' }
		return langTbl.get(displayLang, None)