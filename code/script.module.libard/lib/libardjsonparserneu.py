#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import json
import re
import libmediathek3 as libMediathek

if sys.version_info[0] < 3: # for Python 2
	from urllib import urlencode
else: # for Python 3
	from urllib.parse import urlencode
	from functools import reduce

baseUrlJson = 'https://api.ardmediathek.de/public-gateway?'
baseUrlHtml = 'http://www.ardmediathek.de/ard/player/'

keyOperationName = 'operationName'
keyVariables = 'variables'
keyExtensions = 'extensions'
extensions = '{"persistedQuery":{"version":1,"sha256Hash":"%s"}}'
pageNames = ('showsPage','programPage','defaultPage','playerPage','showPage')
pageIndexAZPage = 0
pageIndexProgramPage = 1
pageIndexLivestreamPage = 2
pageIndexPlayerPage = 3
pageIndexShowPage = 4


def deep_get(dictionary, keys, default=None):
	return reduce(lambda d, key: d.get(key, default) if isinstance(d, dict) else default, keys.split('.'), dictionary)

def parseLivestreams(partnerKey, clientKey):
	pageIndex = pageIndexLivestreamPage
	variables = '{"client":"%s","name":"home","personalized":false}'
	sha256Hash = '9995d49ccbd97dfb67357e9e3505e4f022e405d0ad23fc3d21dd36c2e2de7bb8'
	queryParams = {}
	queryParams[keyOperationName] = pageNames[pageIndex]
	queryParams[keyVariables] = variables % clientKey
	queryParams[keyExtensions] = extensions % sha256Hash
	url = baseUrlJson + urlencode(queryParams)
	return parse(pageIndex, url, partnerKey)

def parseAZ(clientKey, letter):
	pageIndex = pageIndexAZPage
	variables = '{"client":"%s"}'
	sha256Hash = '98428cf5620ad85b703f425bd17970f25bd6da2126a06f12571317d27998039b'
	queryParams = {}
	queryParams[keyOperationName] = pageNames[pageIndex]
	queryParams[keyVariables] = variables % clientKey
	queryParams[keyExtensions] = extensions % sha256Hash
	url = baseUrlJson + urlencode(queryParams)
	return parseLetter(pageIndex, url, letter)

def parseShow(showId):
	pageIndex = pageIndexShowPage
	variables = '{"client":"ard","showId":"%s","pageNumber":0}'
	sha256Hash = '85a89bbc543e4054aa600e4209faeb625d566c5aec44c37d6f7c231785c0d0e6'
	queryParams = {}
	queryParams[keyOperationName] = pageNames[pageIndex]
	queryParams[keyVariables] = variables % showId
	queryParams[keyExtensions] = extensions % sha256Hash
	url = baseUrlJson + urlencode(queryParams)
	return parse(pageIndex, url)

def parseDate(partnerKey, clientKey, date):
	pageIndex = pageIndexProgramPage
	variables = '{"client":"%s","startDate":"%s"}'
	sha256Hash = 'b3f152bfb679d8246594cf7f807860acdb1bf5479801dcace1307d6f6e2a2e23'
	queryParams = {}
	queryParams[keyOperationName] = pageNames[pageIndex]
	queryParams[keyVariables] = variables % (clientKey, date) # date = YYYY-MM-DD
	queryParams[keyExtensions] = extensions % sha256Hash
	url = baseUrlJson + urlencode(queryParams)
	channelKey = clientKey if partnerKey else None
	return parse(pageIndex, url, partnerKey, channelKey)

def getVideoUrl(clipId):
	pageIndex = pageIndexPlayerPage
	variables = '{"client":"ard","clipId":"%s","deviceType":"mobi"}'
	sha256Hash = '893d15418a9fa569150f104722867e0f6cf39afd443cd53a33aa500e094e0032'
	queryParams = {}
	queryParams[keyOperationName] = pageNames[pageIndex]
	queryParams[keyVariables] = variables % clipId
	queryParams[keyExtensions] = extensions % sha256Hash
	url = baseUrlJson + urlencode(queryParams)
	return parseVideo(pageIndex, url)

def parseVideo(pageIndex, url):
	result = None
	response = libMediathek.getUrl(url)
	j = json.loads(response)
	mediaCollection = deep_get(j, 'data.' + pageNames[pageIndex] + '.mediaCollection')
	if mediaCollection:
		mediaArray = mediaCollection.get('_mediaArray',None)
		if mediaArray:
			mediaStreamArray = mediaArray[0].get('_mediaStreamArray',None)
			if mediaStreamArray:
				result = extractBestQuality(mediaStreamArray, lambda x: x[0])
		if result:
			subtitleUrl = mediaCollection.get('_subtitleUrl',None)
			if subtitleUrl:
				result['subtitle'] = [{'url':subtitleUrl, 'type': 'ttml', 'lang':'de'}]
	return result

def parseSearchHtml(url):
	l = []
	response = libMediathek.getUrl(url)
	split = response.split('window.__FETCHED_CONTEXT__');
	if (len(split) > 1):
		json_str = split[1]
		start = 0
		while json_str[start] in (' ','='):
			start += 1
		end = start
		while True:
			while json_str[end] != ';':
				end += 1
			if json_str[end+1:].lstrip().startswith('</script>'): break
			else: end += 1
		json_str = json_str[start:end]
		j = json.loads(json_str)
		for grid_item in j.values():
			if isinstance(grid_item,dict) and (grid_item.get('type',None) == 'gridlist'):
				for item in grid_item.get('teasers',[]):
					if isinstance(item,dict) and (item.get('type',None) == 'ondemand'):
						id = item.get('id',None)
						name = item['shortTitle']
						if id and name:
							d ={}
							d['documentId'] = id
							d['url'] = baseUrlHtml + id
							d['duration'] = str(item.get('duration',None))
							d['name'] = name
							d['plot'] = item.get('longTitle',None)
							d['date'] = item.get('broadcastedOn',None)
							thumb_id = '$Teaser:' + id
							thumb_item = deep_get(item, 'images.aspect16x9')
							if not thumb_item:
								thumb_item = deep_get(item, 'images.aspect1x1')
							if not thumb_item:
								thumb_item = deep_get(item, 'images.aspect16x7')
							if thumb_item:
								thumb_src = thumb_item.get('src','')
								thumb_src = thumb_src.replace('{width}','1024')
								d['thumb'] = thumb_src
							d['_type'] = 'video'
							d['mode'] = 'libArdPlayHtml'
							l.append(d)
	return l

def getVideoUrlHtml(url):
	response = libMediathek.getUrl(url)
	split = response.split('window.__FETCHED_CONTEXT__');
	if (len(split) > 1):
		json_str = split[1]
		start = 0
		while json_str[start] in (' ','='):
			start += 1
		end = start
		while True:
			while json_str[end] != ';':
				end += 1
			if json_str[end+1:].lstrip().startswith('</script>'): break
			else: end += 1
		json_str = json_str[start:end]
		j = json.loads(json_str)
		for item in j.values():
			widgets = item.get('widgets',None)
			if widgets:
				for widget in widgets:
					if widget.get('type',None) == 'player_ondemand':
						mediaCollection = deep_get(widget, 'mediaCollection.embedded._mediaArray')
						if mediaCollection and isinstance(mediaCollection,list) and isinstance(mediaCollection[0],dict): 
							return extractBestQuality(mediaCollection[0].get('_mediaStreamArray',[]), lambda x: None if isinstance(x,list) else x)
	return None

def extractBestQuality(streams, fnGetFinalUrl):
	media = []
	for item in streams:
		if isinstance(item,dict) and (item.get('__typename','MediaStreamArray') == 'MediaStreamArray'):
			stream = item.get('_stream',None)
			if stream:
				url = fnGetFinalUrl(stream)
				if url:
					if url.startswith('//'):
						url = 'https:' + url
					quality = item.get('_quality',-1);
					if quality == 'auto':
						media.insert(0,{'url':url, 'type':'video', 'stream':'hls'})
					elif url[-4:].lower() == '.mp4':
						try:
							quality = int(quality)
						except ValueError:
							pass
						else:
							media.append({'url':url, 'type':'video', 'stream':'mp4', 'bitrate':quality})
	ignore_adaptive = libMediathek.getSettingBool('ignore_adaptive')
	while ignore_adaptive and len(media) > 1 and media[0]['stream'] == 'hls':
		del media[0]
	if media: 
		return dict(media = media)
	else: 
		return None

def parse(pageIndex, url, partnerKey=None, channelKey=None):
	result = []
	response = libMediathek.getUrl(url)
	j = json.loads(response)
	data = j.get('data',None)
	if data:
		page = data.get(pageNames[pageIndex],None)
		if page:
			widgets = [page] if pageIndex == pageIndexShowPage else page.get('widgets',[])
			for widget in widgets:
				if (channelKey is None) or (channelKey == widget.get('channelKey',None)):
					teasers = widget.get('teasers',None)
					if teasers:
						for teaser in teasers:
							type = teaser['type']
							publicationService = teaser.get('publicationService',None)
							if (
							 	type in ('live','ondemand','broadcastMainClip','show')
							 	and
								(type == 'live') == (pageIndex == pageIndexLivestreamPage)
								and
								((partnerKey is None) or (publicationService and (partnerKey == publicationService.get('partner',None))))
							):
								documentId = deep_get(teaser, 'links.target.id')
								name = teaser['shortTitle']
								if documentId and name:
									d = {}
									d['documentId'] = documentId
									d['name'] = name
									d['plot'] = teaser.get('longTitle',None)
									if (pageIndex == pageIndexProgramPage) and (partnerKey is None) and publicationService:
										d['name'] = d['name'] + ' | [COLOR blue]' + publicationService['name'] + '[/COLOR]'
									duration = teaser.get('duration', None)
									if duration:
										d['_duration'] = str(duration)
									thumb = deep_get(teaser, 'images.aspect16x9.src')
									if not thumb:
										thumb = deep_get(teaser, 'images.aspect1x1.src')
									if not thumb:
										thumb = deep_get(teaser, 'images.aspect16x7.src')
									if thumb:
										d['thumb'] = (thumb.split('?')[0]).replace('{width}','1024')
									if type == 'show':
										d['_type'] = 'dir'
										d['mode'] = 'libArdListShow'
									else:
										if pageIndex == pageIndexProgramPage:
											d['_airedISO8601'] = teaser.get('broadcastedOn', None)
										if pageIndex == pageIndexLivestreamPage:
											d['_type'] = 'live'
										elif pageIndex == pageIndexProgramPage:
											d['_type'] = 'date'
										else:
											d['_type'] = 'video'
										d['mode'] = 'libArdPlay'
									result.append(d)
	# "Alle Sender nach Datum" ist nicht sinnvoll vorsortiert
	if pageIndex == pageIndexProgramPage and partnerKey is None:
		result.sort(key = lambda x: x.get('_airedISO8601',None))
	return result

def parseLetter(pageIndex, url, letter):
	result = []
	response = libMediathek.getUrl(url)
	j = json.loads(response)
	shows = deep_get(j, 'data.' + pageNames[pageIndex] + '.glossary.shows' + letter, [])
	for teaser in shows:
		type = teaser['type']
		documentId = deep_get(teaser, 'links.target.id')
		name = teaser['shortTitle']
		if type == 'show' and documentId and name:
			d = {}
			d['documentId'] = documentId
			d['name'] = name
			d['plot'] = teaser.get('longTitle',None)
			thumb = deep_get(teaser, 'images.aspect16x9.src')
			if not thumb:
				thumb = deep_get(teaser, 'images.aspect1x1.src')
			if not thumb:
				thumb = deep_get(teaser, 'images.aspect16x7.src')
			if thumb:
				d['thumb'] = (thumb.split('?')[0]).replace('{width}','1024')
			d['_type'] = 'dir'
			d['mode'] = 'libArdListShow'
			result.append(d)
	return result
