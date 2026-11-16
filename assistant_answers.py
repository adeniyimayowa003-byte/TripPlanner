"""Grounded source excerpts. No model, credentials, account or storage access."""
from dataclasses import dataclass
from decimal import Decimal
import re

from help_content import FAQ_VERSION, search_faq


@dataclass(frozen=True)
class Source:
    id: str
    label: str
    text: str
    url: str
    version: str


@dataclass(frozen=True)
class Answer:
    mode: str
    notice: str
    sources: tuple = ()


_KEYWORDS = {
    'cities': 'cities city destinations countries coverage supported',
    'allowance': 'allowance budget money spend spending cover covers included total person',
    'gaps': 'meals meal missing gaps gap empty slots restaurant restaurants incomplete food',
    'estimates': 'price prices hours opening current live booking verified availability',
    'saving': 'cookie cookies cleared lost save saving browser private',
    'snapshots': 'snapshot snapshots historical update updated saved estimate',
    'maps': 'map maps navigation google directions',
    'hosting': 'slow wake waking load loading sleep sleeping demo host hosting quota',
    'native': 'android windows offline native device sync upload downloads synchronize',
    'unavailable': 'account accounts ai assistant chatbot signin subscription',
    'themes': 'theme themes appearance light dark setting settings',
    'support': 'support contact help emergency emergencies ticket',
}
_STOP = set('the a an to of my i in about tell me what why is are how do does can and for with it this'.split())


def faq_source(item):
    return Source('faq:'+item.id,item.question,item.answer,'/help#'+item.id,str(FAQ_VERSION))


def catalog_source(place):
    from money import format_money
    text=(f"{place['name']} — {place['destination']}. {place['description']} "
          f"Illustrative estimate: {place['currency']} {format_money(Decimal(str(place['estimated_cost'])),currency=place['currency'])}. "
          f"{place['cost_note']} Reviewed {place['reviewed_on']}. Check the source before traveling.")
    return Source('catalog:'+place['id'],place['name'],text,
                  '/assistant/sources/'+place['id'],place['reviewed_on'])


def sources_for(question):
    words=set(re.findall(r"[a-z0-9]+",question.casefold()))-_STOP
    faqs=search_faq('')
    ranked=sorted(((len(words & set(_KEYWORDS.get(item.id,'').split())),item) for item in faqs),
                  key=lambda pair:(-pair[0],pair[1].id))
    sources=[faq_source(item) for score,item in ranked[:2] if score]
    # Generic help never depends on a working catalog. Venue/city questions can
    # read only the approved public catalog, never the current draft or saves.
    cities={'paris','lagos','london','york','tokyo','cape'}
    if not sources or words & cities:
        try:
            from catalog import load_catalog
            candidates=[]
            for place in load_catalog():
                terms=set(re.findall(r'[a-z0-9]+',(place['name']+' '+place['destination']).casefold()))
                score=len((words-_STOP)&terms)
                if score:candidates.append((score,place))
            candidates.sort(key=lambda pair:(-pair[0],pair[1]['id']))
            sources.extend(catalog_source(place) for _,place in candidates[:3-len(sources)])
        except (OSError,ValueError,KeyError):
            pass
    return tuple(sources[:3])


def fallback_answer(question,notice=''):
    sources=sources_for(question)
    message=notice or ('Here are the approved project sources that match your question.' if sources else
                      'That information is not verified in TripPlanner. Try a sample question or open Help & FAQs.')
    return Answer('faq',message,sources)
