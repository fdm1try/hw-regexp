import csv
import re
import logging
from itertools import islice

RE_EMAIL = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
RE_PHONE = re.compile(r'\+?([78])(([\s()-]*\d){10})([(добавчный\.\s]*(\d+))?')


class Email:
    """
    The e-mail address, address cannot be changed (__hash__ implemented).
    """
    def __init__(self, address: str):
        email_address = address.strip()
        if not self.__class__.is_valid(email_address):
            raise Exception('Invalid e-mail address!')
        self._address = email_address

    def __str__(self):
        return self.address

    def __eq__(self, other):
        if isinstance(other, str):
            return self.address == other
        if isinstance(other, Email):
            return self.address == other.address
        return False

    def __hash__(self):
        return hash(self._address)

    @staticmethod
    def is_valid(address: str):
        """
        :param address: the e-mail address
        :return: True if e-mail address is correct
        """
        return RE_EMAIL.match(address.strip())

    @staticmethod
    def parse(address: str):
        """
        :param address: the e-mail address
        :return: Email instance if address is correct
        """
        return Email(address) if Email.is_valid(address) else None

    @property
    def address(self):
        return self._address


class Phone:
    """
    Phone number. The phone number, including the country code and extension number,
    cannot be changed - they are involved in the __hash__ function.
    """
    def __init__(self, int_code: int, number: str, ext_code: str = None):
        self._int_code = int_code
        self._number = re.sub(r'\D', '', number)
        self._ext_code = ext_code

    def __str__(self):
        phone_number = re.sub(r"(\d{3})(\d{3})(\d{2})(\d{2})", "(\\1)\\2-\\3-\\4", self._number)
        ext_code = f' доб.{self.ext_code}' if self.ext_code else ''
        return f'+{self.int_code}{phone_number}{ext_code}'

    def __eq__(self, other):
        if isinstance(other, Phone):
            return self.int_code == other.int_code and self.number == other.number \
                   and self.ext_code == other.ext_code
        if isinstance(other, str):
            return self == Phone.parse_ru(other)
        return False

    def __hash__(self):
        return hash(f'{self._int_code}{self._number}{self._ext_code}')

    @staticmethod
    def parse_ru(number: str):
        """
        :param number: a string containing a phone number, you can specify an extension сode
        :return: Phone if number is correct
        """
        match = RE_PHONE.search(number)
        if not match:
            return
        phone_number = re.sub(r'\D', '', match.group(2))
        if len(match.groups()) > 4:
            ext_code = match.group(5)
        return Phone(7, phone_number, ext_code)

    @property
    def int_code(self):
        return self._int_code

    @property
    def number(self):
        return self._number

    @property
    def ext_code(self):
        return self._ext_code


class Contact:
    """
    Stores contact information
    """
    def __init__(self, first_name: str, last_name: str, surname: str = None, org: str = None, position: str = None,
                 phone: Phone = None, email: Email = None):
        """
        :param first_name: first name
        :param last_name: last name
        :param surname: surname
        :param org: place of work (organization)
        :param position: position in the organization
        :param phone: phone number
        :param email: e-mail address
        """
        self.first_name = first_name
        self.last_name = last_name
        self.surname = surname
        self.org = org
        self.position = position
        self.phone = phone
        self.email = email

    def __str__(self):
        result = ' '.join([self.last_name.title(), self.first_name.title(), self.surname.title()])
        if self.position:
            result += f', {self.position}'
        if self.org:
            result += f'({self.org})'
        if self.phone:
            result += f', {self.phone}'
        if self.email:
            result += f' [{self.email}]'
        return result


class Phonebook:
    """
    Phone book, stores contacts, the list is available in the list property.
    """
    def __init__(self):
        self._list = []
        self._hash = {}

        self.conflicts = []

    @property
    def list(self):
        return list(self._list[:])

    def add(self, contact: Contact):
        """
        :param contact: the contact being added
        :return: True if there were no conflicts, if returned False - the conflict is added to the conflicts list
        """
        if duplicate := (self._hash.get(contact.email) or self._hash.get(contact.phone)):
            self.conflicts.append(PhonebookConflict(self, duplicate, contact))
            return False
        if duplicate := self._hash.get(contact.last_name + contact.first_name):
            if not duplicate.surname or not contact.surname or duplicate.surname == contact.surname:
                self.conflicts.append(PhonebookConflict(self, duplicate, contact))
                return False
        self._list.append(contact)
        if contact.email:
            self._hash[contact.email] = contact
        if contact.phone:
            self._hash[contact.phone] = contact
        self._hash[contact.last_name + contact.first_name] = contact
        return Contact

    def load_csv_file(self, path: str):
        """
        :param path: path to the csv file
        :return: None
        """
        with open(path, encoding='utf-8', newline='') as f:
            for row in islice(csv.reader(f, delimiter=","), 1, None):
                full_name = ' '.join(row[:3]).strip().split(' ')
                self.add(Contact(
                    last_name=full_name[0] if len(full_name) else None,
                    first_name=full_name[1] if len(full_name) > 1 else None,
                    surname=full_name[2] if len(full_name) > 2 else None,
                    org=row[3].strip() if len(row[3].strip()) else None,
                    position=row[4].strip() if len(row[4].strip()) else None,
                    phone=Phone.parse_ru(row[5]),
                    email=Email.parse(row[6])
                ))

    def save_csv_file(self, path: str):
        """
        :param path: path to the csv file
        :return: None
        """
        if not path.endswith('.csv'):
            path += '.csv'
        csv_header = ['lastname', 'firstname', 'surname', 'organization', 'position', 'phone', 'email']
        with open(path, 'w', encoding='utf-8', newline='') as f:
            csv.writer(f, ).writerows([csv_header] + [
                [item.last_name, item.first_name, item.surname, item.org, item.position, item.phone, item.email]
                for item in self._list
            ])


class PhonebookConflict:
    """
    In case of a conflict when adding a new contact, this class is used.
    In which source is the original contact, and dest is a duplicate record.
    """
    def __init__(self, pb: Phonebook, source: Contact, dest: Contact):
        self.phonebook = pb
        self.source = source
        self.dest = dest
        self.resolved = False

    def merge(self, ignore: list = []):
        """
        :param ignore: these attributes will not be overwritten,
        there may be a first_name, last_name, surname, org, position, phone or email.
        :return: Overwrites the attributes of the original contact if they are specified in the duplicate.
        Marks the resolved property to True, returns None.
        """
        for key in ['first_name', 'last_name', 'surname', 'org', 'position', 'phone', 'email']:
            new_value = self.dest.__getattribute__(key)
            if key in ignore or not new_value or new_value == self.source.__getattribute__(key):
                continue
            self.source.__setattr__(key, new_value)
        self.resolved = True


if __name__ == '__main__':
    phonebook = Phonebook()
    phonebook.load_csv_file('phonebook_raw.csv')
    for conflict in phonebook.conflicts:
        logging.warning(f' Duplicate contact found: {conflict.source}')
        conflict.merge()
        logging.warning(f' Contact information changed to: {conflict.source}')
    phonebook.save_csv_file('phonebook.csv')
