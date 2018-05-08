#!/usr/bin/env python
# vim:fileencoding=utf-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
						print_function)

__license__   = 'GPL v3'
__copyright__ = '2011-2018, Hoffer Csaba <csaba.hoffer@gmail.com>, Kloon <kloon@techgeek.co.in>, otapi <otapigems.com>'
__docformat__ = 'restructuredtext hu'

import time
import urllib
from Queue import Queue, Empty
from lxml.html import fromstring
import lxml.etree as etree
from calibre import as_unicode
from calibre.ebooks.metadata import check_isbn
from calibre.ebooks.metadata.sources.base import Source, Option
from calibre.utils.cleantext import clean_ascii_chars
import lxml, sys, traceback
from calibre import browser

class Moly_hu(Source):
	name					= 'Moly_hu'
	description				= _('Downloads metadata and covers from moly.hu')
	author					= 'Hoffer Csaba & Kloon & fatsadt & otapi'
	version					= (1, 0, 7)
	minimum_calibre_version = (0, 8, 0)

	capabilities = frozenset(['identify', 'cover'])
	touched_fields = frozenset(['title', 'authors', 'identifier:isbn', 'identifier:moly_hu', 'tags', 'comments', 'rating', 'series', 'series_index', 'publisher', 'pubdate', 'language', 'languages'])
	has_html_comments = False
	supports_gzip_transfer_encoding = False
	can_get_multiple_covers = True

	KEY_MAX_BOOKS = 'max_books'
	KEY_MAX_COVERS = 'max_covers'

	options = (Option(KEY_MAX_BOOKS, 'number', 3, _('Maximum number of books to get'),
                      _('The maximum number of books to process from the moly.hu search result')),
				Option(KEY_MAX_COVERS, 'number', 5, _('Maximum number of covers to get'),
                      _('The maximum number of covers to process for the chosen book'))
	)

	BASE_URL = 'https://moly.hu'
	BOOK_URL = BASE_URL + '/konyvek/'
	SEARCH_URL = BASE_URL + '/kereses?utf8=%E2%9C%93&q='

	def create_query(self, log, title=None, authors=None, identifiers={}):
		if title is not None:
			search_title = urllib.quote(title.encode('utf-8'))
		else:
			search_title = ''

		if authors is not None:
			search_author = urllib.quote(authors[0].encode('utf-8'))
		else:
			search_author = ''

		search_page = Moly_hu.SEARCH_URL + '%s+%s'%(search_author, search_title)

		return search_page
	def get_cached_cover_url(self, identifiers):
		url = None
		moly_id = identifiers.get('moly_hu', None)
		if moly_id is None:
			isbn = check_isbn(identifiers.get('isbn', None))
			if isbn is not None:
				moly_id = self.cached_isbn_to_identifier(isbn)
		if moly_id is not None:
			url = self.cached_identifier_to_cover_url(moly_id)
		return url

	def identify(self, log, result_queue, abort, title, authors,
			identifiers={}, timeout=30):
		'''
		Note this method will retry without identifiers automatically if no
		match is found with identifiers.
		'''
		matches = []
		moly_id = identifiers.get('moly_hu', None)
		log.info(u'\nTitle:%s\nAuthors:%s\n'%(title, authors))
		br = browser()
		if moly_id:
			matches.append(Moly_hu.BOOK_URL + moly_id)
		else:
			query = self.create_query(log, title=title, authors=authors, identifiers=identifiers)
			if query is None:
				log.error('Insufficient metadata to construct query')
				return
			try:
				log.info('Querying: %s'%query)
				response = br.open(query)
			except Exception as e:
				if callable(getattr(e, 'getcode', None)) and e.getcode() == 404:
					log.info('Failed to find match for ISBN: %s'%isbn)
				else:
					err = 'Failed to make identify query: %r'%query
					log.exception(err)
					return as_unicode(e)

			try:
				raw = response.read().strip()
				raw = raw.decode('utf-8', errors='replace')
				if not raw:
					log.error('Failed to get raw result for query: %r'%query)
					return
				root = fromstring(clean_ascii_chars(raw))
			except:
				msg = 'Failed to parse moly.hu page for query: %r'%query
				log.exception(msg)
				return msg
			self._parse_search_results(log, title, authors, root, matches, timeout)

		if abort.is_set():
			return

		if not matches:
			if identifiers and title and authors:
				log.info('No matches found with identifiers, retrying using only'
						' title and authors')
				return self.identify(log, result_queue, abort, title=title,
						authors=authors, timeout=timeout)
			log.error('No matches found with query: %r'%query)
			return

		from calibre_plugins.moly_hu.worker import Worker
		workers = [Worker(url, result_queue, br, log, i, self) for i, url in
				enumerate(matches)]

		for w in workers:
			w.start()
			time.sleep(0.1)
		
		
		while not abort.is_set():
			a_worker_is_alive = False
			for w in workers:
				w.join(0.2)
				if abort.is_set():
					break
				if w.is_alive():
					a_worker_is_alive = True
			if not a_worker_is_alive:
				break

		return None
	def _parse_search_results(self, log, orig_title, orig_authors, root, matches, timeout):
		max_results = self.prefs[Moly_hu.KEY_MAX_BOOKS]
		results = root.xpath('//a[@class="book_selector"]')
		log.info('Found %d possible books (max: %d)'%(len(results), max_results))
		i = 0
		for result in results:
			book_urls = result.xpath('@href')
			etree.strip_tags(result, 'strong')
			author_n_title = result.text
			author_n_titles = author_n_title.split(':', 1)
			author = author_n_titles[0].strip(' \r\n\t')
			title = author_n_titles[1].strip(' \r\n\t')
			log.info('Orig: %s, target: %s'%(self.strip_accents(orig_title), self.strip_accents(title)))
			
			if orig_title:
				if orig_title.lower() not in title.lower() and self.strip_accents(orig_title) not in self.strip_accents(title):
					continue
			if orig_authors:
				author1 = orig_authors[0]
				authorsplit = author1.split(" ")
				author2 = author1
				if len(authorsplit) > 1:
					author2 = '%s %s'%(authorsplit[1], authorsplit[0])
				if author1.lower() not in author.lower() and self.strip_accents(author1) not in self.strip_accents(author) and author2.lower() not in author.lower() and self.strip_accents(author2) not in self.strip_accents(author):
					continue
			
			for book_url in book_urls:
				result_url = Moly_hu.BASE_URL + book_url
				
				if (result_url not in matches):
					matches.append(result_url)
					i += 1
				if (i >= max_results):
					return
		
	def strip_accents(self, s):
		symbols = (u"öÖüÜóÓőŐúÚéÉáÁűŰíÍ",
                   u"oOuUoOoOuUeEaAuUiI")

		tr = dict( [ (ord(a), ord(b)) for (a, b) in zip(*symbols) ] )

		return s.translate(tr).lower()
		
	def download_cover(self, log, result_queue, abort, title=None, authors=None, identifiers={}, timeout=30, get_best_cover=False):
		if not title:
			return
		urls = self.get_image_urls(title, authors, identifiers, log, abort, timeout)
		self.download_multiple_covers(title, authors, urls, get_best_cover, timeout, result_queue, abort, log)

	def get_image_urls(self, title, authors, identifiers, log, abort, timeout):
		cached_url = self.get_cached_cover_url(identifiers)
		if cached_url is None:
			log.info('No cached cover found, running identify')
			rq = Queue()
			self.identify(log, rq, abort, title=title, authors=authors, identifiers=identifiers)
			if abort.is_set():
				return
			results = []
			while True:
				try:
					results.append(rq.get_nowait())
				except Empty:
					break
			results.sort(key=self.identify_results_keygen(
				title=title, authors=authors, identifiers=identifiers))
			for mi in results:
				cached_url = self.get_cached_cover_url(mi.identifiers)
				if cached_url is not None:
					break

		if cached_url is not None:
			return cached_url

		log.info('No cover found')
		return []
