from english_words import get_english_words_set  

import random
import os

class EmailGenerator():
    DATA = { 'web2lowerset': None, 'already-assigned-aliases-pathname': None, 'aliases': None }

    @staticmethod
    def _get_random_email(domain):
        first_word = EmailGenerator.DATA['web2lowerset'][random.randint(0, len(EmailGenerator.DATA['web2lowerset']) - 1)]
        second_word = EmailGenerator.DATA['web2lowerset'][random.randint(0, len(EmailGenerator.DATA['web2lowerset']) - 1)]
        number = random.randint(0, 999)
        return '%s_%s%03d@%s' % (first_word, second_word, number, domain)

    @staticmethod
    def _read_already_assigned_aliases(already_assigned_aliases_pathname):
        aliases = []
        if os.path.isfile(already_assigned_aliases_pathname):
            with open(already_assigned_aliases_pathname,'r') as lines:
                for line in lines:
                       data = line.rstrip("\n").split(':', 1)
                       aliases.append(data[0])
        return aliases

    @staticmethod
    def _write_already_assigned_aliases(already_assigned_aliases_pathname, alias):
        file = open(already_assigned_aliases_pathname,'a+')
        file.write(alias + "\n")
        file.close()

    @staticmethod
    def initialize(already_assigned_aliases_pathname):
        if EmailGenerator.DATA['web2lowerset'] is None: EmailGenerator.DATA['web2lowerset'] = list(get_english_words_set(['web2'], lower = True, alpha = True))
        if (already_assigned_aliases_pathname != EmailGenerator.DATA['already-assigned-aliases-pathname']):
            EmailGenerator.DATA['already-assigned-aliases-pathname'] = already_assigned_aliases_pathname
            EmailGenerator.DATA['aliases'] = EmailGenerator._read_already_assigned_aliases(EmailGenerator.DATA['already-assigned-aliases-pathname'])

    @staticmethod
    def get_random_email(domain, description = None):
        while (True):
            alias = EmailGenerator._get_random_email(domain)
            if alias not in EmailGenerator.DATA['aliases']: break
        EmailGenerator.DATA['aliases'].append(alias)
        EmailGenerator._write_already_assigned_aliases(EmailGenerator.DATA['already-assigned-aliases-pathname'], '%s:%s' % ( alias, description if description is not None else '' ))
        return alias



