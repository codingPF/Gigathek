# -*- coding: utf-8 -*-
import sys
import libsrjsonparser as libSrJsonParser
import libmediathek3 as libMediathek

translation = libMediathek.getTranslation
params = libMediathek.get_params() 

#http://hbbtv.sr-mediathek.de/inc/SearchJSON.php

def list():
	return libMediathek.list(modes, 'libSrListMain', 'libSrPlay')

def libSrListMain():
	l = []
	l.append({'name':translation(31030), 'mode':'libSrListVideos', 'urlargs':'{}', '_type':'dir'})
	l.append({'name':translation(31032), 'mode':'libSrListShows', '_type':'dir'})
	l.append({'name':translation(31033), 'mode':'libSrListDate', '_type':'dir'})
	l.append({'name':translation(31035), 'mode':'libSrListTopics', '_type':'dir'})
	l.append({'name':translation(31039), 'mode':'libSrListSearch', '_type':'dir'})
	return l

def libSrListDate():
	return libMediathek.populateDirDate('libSrListDateVideos')

def libSrListDateVideos():
	return libSrJsonParser.getDate(params['datum'])

def libSrListShows():
	libMediathek.sortAZ()
	return libSrJsonParser.getShows()

def libSrListTopics():
	libMediathek.sortAZ()
	return libSrJsonParser.getTopics()

def libSrListTopic():
	return libSrJsonParser.getTopic(params['t_kurz'])

def libSrListVideos():
	#libMediathek.log(str(params))
	return libSrJsonParser.getSearch(params['urlargs'])

def libSrListSearch():
	search_string = libMediathek.getSearchString()
	return libSrJsonParser.getSearch('{"suche":"'+search_string+'"}') if search_string else None

def libSrPlay():
	result = libSrJsonParser.getVideoUrl(params['id'])
	result = libMediathek.getMetadata(result)
	return result

modes = {
	'libSrListMain': libSrListMain,
	'libSrListShows': libSrListShows,
	'libSrListVideos': libSrListVideos,
	'libSrListDate': libSrListDate,
	'libSrListDateVideos': libSrListDateVideos,
	'libSrListTopics': libSrListTopics,
	'libSrListTopic': libSrListTopic,
	'libSrPlay': libSrPlay,
	'libSrListSearch': libSrListSearch,
}
