# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage.  If not, see <http://www.gnu.org/licenses/>.
import threading
import sickbeard
from sickbeard import db
from sickbeard import logger

nameCache = {}
nameCacheLock = threading.Lock()

def addNameToCache(name, indexer_id=0):
    """
    Adds the show & tvdb id to the scene_names table in cache.db.
    
    name: The show name to cache
    indexer_id: the TVDB and TVRAGE id that this show should be cached with (can be None/0 for unknown)
    """
    global nameCache

    cacheDB = db.DBConnection('cache.db')

    # standardize the name we're using to account for small differences in providers
    name = sickbeard.helpers.full_sanitizeSceneName(name)
    if name not in nameCache:
        nameCache[name] = int(indexer_id)
        cacheDB.action("INSERT OR REPLACE INTO scene_names (indexer_id, name) VALUES (?, ?)", [indexer_id, name])


def retrieveNameFromCache(name):
    """
    Looks up the given name in the scene_names table in cache.db.
    
    name: The show name to look up.
    
    Returns: the TVDB and TVRAGE id that resulted from the cache lookup or None if the show wasn't found in the cache
    """
    global nameCache

    name = sickbeard.helpers.full_sanitizeSceneName(name)
    if name in nameCache:
        return int(nameCache[name])

def clearCache():
    """
    Deletes all "unknown" entries from the cache (names with indexer_id of 0).
    """
    global nameCache

    # init name cache
    if not nameCache:
        nameCache = {}

    cacheDB = db.DBConnection('cache.db')
    cacheDB.action("DELETE FROM scene_names WHERE indexer_id = ?", [0])

    toRemove = [key for key, value in nameCache.iteritems() if value == 0]
    for key in toRemove:
        del nameCache[key]


def saveNameCacheToDb():
    cacheDB = db.DBConnection('cache.db')

    for name, indexer_id in nameCache.items():
        cacheDB.action("INSERT OR REPLACE INTO scene_names (indexer_id, name) VALUES (?, ?)", [indexer_id, name])


def buildNameCache(show=None):
    global nameCache

    with nameCacheLock:
        # clear internal name cache
        clearCache()

        # update scene exception names
        sickbeard.scene_exceptions.retrieve_exceptions()

        if not show:
            logger.log(u"Building internal name cache for all shows", logger.INFO)

            cacheDB = db.DBConnection('cache.db')
            cache_results = cacheDB.select("SELECT * FROM scene_names")
            for cache_result in cache_results:
                name = sickbeard.helpers.full_sanitizeSceneName(cache_result["name"])
                if name in nameCache:
                    continue

                indexer_id = int(cache_result["indexer_id"])
                nameCache[name] = indexer_id

            for show in sickbeard.showList:
                for curSeason in [-1] + sickbeard.scene_exceptions.get_scene_seasons(show.indexerid):
                    for name in list(set(
                                    sickbeard.scene_exceptions.get_scene_exceptions(show.indexerid, season=curSeason) + [
                                show.name])):
                        name = sickbeard.helpers.full_sanitizeSceneName(name)
                        if name in nameCache:
                            continue

                        nameCache[name] = int(show.indexerid)
        else:
            logger.log(u"Building internal name cache for " + show.name, logger.INFO)

            for curSeason in [-1] + sickbeard.scene_exceptions.get_scene_seasons(show.indexerid):
                for name in list(set(sickbeard.scene_exceptions.get_scene_exceptions(show.indexerid, season=curSeason) + [
                    show.name])):
                    name = sickbeard.helpers.full_sanitizeSceneName(name)
                    if name in nameCache:
                        continue

                    nameCache[name] = int(show.indexerid)

        logger.log(u"Internal name cache set to: " + str(nameCache), logger.DEBUG)