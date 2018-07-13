import re

from ..util import legistar_id_guid

from .base import BaseCollector


DATA_IDENTIFIERS = dict(
    firstname='_lblFirst',
    lastname='_lblLast',
    website='_hypWebSite',
    notes='_lblNotes',
    photo_link='_imgPhoto',
    )
# photo_link no longer on people page
#    photo_link='_imgPhoto'
#    )


# dave ware's page
# https://hattiesburg.legistar.com/PersonDetail.aspx?ID=83530&GUID=62048E45-5276-44A8-8413-19B46071AA96&Search=
# I will probably need to start using selenium to collect
# the information from legistar, as a full list of people
# is only available through a javascript post.
# dware_link = 'PersonDetail.aspx?ID=83530&GUID=62048E45-5276-44A8-8413-19B46071AA96&Search=' # noqa

class PeopleCollector(BaseCollector):
    def __init__(self):
        BaseCollector.__init__(self)
        self.people_url = 'https://hattiesburg.legistar.com/People.aspx'
        self.url_prefix = 'https://hattiesburg.legistar.com/'

    def _get_people_anchors(self):
        self.set_url(self.people_url)
        self.retrieve_page()
        marker = '_hypPerson'
        exp = re.compile('.+%s$' % marker)
        return self.soup.find_all('a', id=exp)

    def _get_people_links(self):
        anchors = self._get_people_anchors()
        people_links = []
        for anchor in anchors:
            people_links.append(anchor['href'])
        # FIXME: hacky way of putting former people
        # into database.  This is done manually until
        # a better way of accessing the website presents
        # itself.
        # people_links.append(dware_link)
        return people_links

    def get_people_ids(self):
        anchors = self._get_people_anchors()
        ids = {}
        for anchor in anchors:
            name = anchor.text.strip()
            id, guid = legistar_id_guid(anchor['href'])
            ids[id] = name
        return ids

    def _get_person_page(self, link):
        url = self.url_prefix + link
        self.set_url(url)
        self.retrieve_page()

    def _get_person(self, page):
        markers = DATA_IDENTIFIERS
        item_keys = list(markers.keys())
        item = {}.fromkeys(item_keys)
        for key in item_keys:
            if key == 'photo_link':
                no_pix = False
            exp = re.compile('.+%s$' % markers[key])
            tags = page.find_all('span', id=exp)
            ttype = 'span'
            if not tags:
                tags = page.find_all('a', id=exp)
                ttype = 'a'
            if not tags:
                tags = page.find_all('img', id=exp)
                ttype = 'img'
            if not tags:
                if ttype == 'img' and key == 'photo_link':
                    no_pix = True
                else:
                    raise RuntimeError("no tags found for %s" % key)
            if len(tags) > 1:
                print("len(%s) == %d" % (key, len(tags)))
            if key == 'photo_link':
                if not no_pix:
                    tag = tags[0]
                    item[key] = tag['src']
                else:
                    item[key] = None
                continue
            tag = tags[0]
            if key == 'website':
                # item[key] = tag['href']
                item[key] = tag.text.strip()
                continue
            item[key] = tag.text.strip()
            print(key, item[key])
        item['id'], item['guid'] = legistar_id_guid(self.url)
        return item

    def collect(self):
        # self.retrieve_page(self.url)
        # self.item = self._get_item(self.soup)
        people = []
        links = self._get_people_links()
        for link in links:
            self._get_person_page(link)
            person = self._get_person(self.soup)
            people.append(person)
        self.people = people
        self.result = self.people


if __name__ == "__main__":
    pc = PeopleCollector()
    # pc.collect()
