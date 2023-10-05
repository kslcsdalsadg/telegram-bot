from english_words import get_english_words_set  

import random
import os

class EmailGenerator():
    DATA = { 'web2lowerset': None, 'already-assigned-emails-pathname': None, 'emails': None }

    @staticmethod
    def _get_random_email(domain):
        first_word = EmailGenerator.DATA['web2lowerset'][random.randint(0, len(EmailGenerator.DATA['web2lowerset']) - 1)]
        second_word = EmailGenerator.DATA['web2lowerset'][random.randint(0, len(EmailGenerator.DATA['web2lowerset']) - 1)]
        number = random.randint(0, 999)
        return '%s_%s%03d@%s' % (first_word, second_word, number, domain)

    @staticmethod
    def _read_already_assigned_emails():
        emails = []
        if os.path.isfile(EmailGenerator.DATA['already-assigned-emails-pathname']):
            with open(EmailGenerator.DATA['already-assigned-emails-pathname'], 'r') as file:
                for line in file:
                    data = line.strip().split(':', 1)
                    if data[0] is not None and not data[0].startswith('#'): 
                        emails.append(data[0])
        return emails

    @staticmethod
    def _search_for_stored_email(email):
        if os.path.isfile(EmailGenerator.DATA['already-assigned-emails-pathname']):
            with open(EmailGenerator.DATA['already-assigned-emails-pathname'], 'r') as file:
                for line in file:
                       data = line.strip().split(':', 1)
                       if email == data[0]: return '%s (%s)' % (data[0], data[1]) if data[1] is not None else data[0]
        return None

    @staticmethod
    def _write_already_assigned_emails(email, description = None):
        with open(EmailGenerator.DATA['already-assigned-emails-pathname'], 'a+') as file:
            file.write("%s:%s\n" % (email, description if description is not None else ''))

    @staticmethod
    def initialize(already_assigned_emails_pathname):
        if EmailGenerator.DATA['web2lowerset'] is None: EmailGenerator.DATA['web2lowerset'] = list(get_english_words_set(['web2'], lower = True, alpha = True))
        if (already_assigned_emails_pathname != EmailGenerator.DATA['already-assigned-emails-pathname']):
            EmailGenerator.DATA['already-assigned-emails-pathname'] = already_assigned_emails_pathname
            EmailGenerator.DATA['emails'] = EmailGenerator._read_already_assigned_emails()

    @staticmethod
    def get_random_email(domain, description = None):
        while (True):
            email = EmailGenerator._get_random_email(domain)
            if email not in EmailGenerator.DATA['emails']: break
        EmailGenerator.DATA['emails'].append(email)
        EmailGenerator._write_already_assigned_emails(email, description)
        return EmailGenerator._search_for_stored_email(email)

