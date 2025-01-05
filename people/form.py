"""
This module provides the journal query form.
"""

import backendcore.data.form_filler as ff

from people.fields import (
    AFFILIATION,
    BIO,
    EMAIL,
    NAME,
    POSITION,
    ROLES,
    USER_ID,
)

import people.roles as rls

FORM_FLDS = [
    {
        ff.FLD_NM: NAME,
        ff.QSTN: 'Name:',
        ff.PARAM_TYPE: ff.QUERY_STR,
        ff.OPT: True,
    },
    {
        ff.FLD_NM: ROLES,
        ff.QSTN: 'Roles:',
        ff.PARAM_TYPE: ff.QUERY_STR,
        ff.CHOICES: rls.get_choices(),
        ff.MULTI: True,
        ff.OPT: True,
    },
    {
        ff.FLD_NM: USER_ID,
        ff.QSTN: 'User_ID:',
        ff.PARAM_TYPE: ff.QUERY_STR,
        ff.OPT: True,
    },
]


ADD_FORM_ADDITIONAL_FLDS = [
    {
        ff.FLD_NM: EMAIL,
        ff.QSTN: 'Email:',
        ff.OPT: True,
    },
    {
        ff.FLD_NM: AFFILIATION,
        ff.QSTN: 'Affiliation:',
        ff.OPT: True,
    },
    {
        ff.FLD_NM: POSITION,
        ff.QSTN: 'Position',
        ff.OPT: True,
    },
    {
        ff.FLD_NM: BIO,
        ff.QSTN: 'Bio:',
        ff.OPT: True,
        ff.FLD_LEN: 255,
    },
]

ADD_FORM = FORM_FLDS + ADD_FORM_ADDITIONAL_FLDS
UPDATE_FORM = ADD_FORM


def get_form() -> list:
    return FORM_FLDS


def get_add_form() -> list:
    return ADD_FORM


def get_update_form() -> list:
    return UPDATE_FORM


def get_form_descr():
    """
    For Swagger!
    """
    return ff.get_form_descr(FORM_FLDS)


def get_fld_names() -> list:
    return ff.get_fld_names(FORM_FLDS)


def main():
    print(f'Form: {get_add_form()=}')
    print(f'Form: {get_form_descr()=}')
    print(f'Field names: {get_fld_names()=}')


if __name__ == "__main__":
    main()
