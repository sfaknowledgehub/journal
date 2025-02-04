"""
This is our interface to our manuscript data.
We never expect our users to add or delete manuscripts,
so we make no provisions for that.
"""
import os
import glob
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

import pypandoc as pdc

from backendcore.data.caching import needs_cache, get_cache
from backendcore.common.constants import (
    CODE,
    EMAIL,
    NAME,
)
import backendcore.common.time_fmts as tfmt
from backendcore.emailer.api_send import send_mail

from journal_common.common import get_collect_name

import people.query as pqry
from people.roles import (
    AU,
    ED,
    RE,
    ROLES,
)

from manuscripts.core.fields import (
    ABSTRACT,
    AUTHORS,
    HISTORY,
    LAST_UPDATED,
    OBJ_ID_NM,
    REFEREES,
    REF_REPORT,
    REF_VERDICT,
    STATE,
    TEXT,
    TITLE,
    WCOUNT,
)

from manuscripts.core.add_form import ( # noqa E402
    FILE,
    MANU_FILE,
    TEXT_ENTRY,
)

import manuscripts.core.states as mst
from manuscripts.core.states import (
    ACCEPT,
    ACCEPT_W_REV,
    ASSIGN_REFEREE,
    AUTHOR_REVIEW,
    AUTHOR_REVISIONS,
    COPY_EDITING,
    DONE,
    EDITOR_MOVE,
    EDITOR_REVIEW,
    FORMATTING,
    PUBLISHED,
    REFEREE_REVIEW,
    REJECT,
    REJECTED,
    REMOVE_REFEREE,
    SUBMITTED,
    SUBMIT_REVIEW,
    WITHDRAW, WITHDRAWN,
)


DB = 'journalDB'
COLLECT = 'manuscripts'
CACHE_NM = COLLECT

# Here's what refs can say about a manuscript.
VERDICTS = [
    ACCEPT,
    ACCEPT_W_REV,
    REJECT,
]


def get_ref_verdicts() -> list:
    return VERDICTS


def is_valid_verdict(verdict: str) -> bool:
    return verdict in get_ref_verdicts()


def needs_manuscripts_cache(fn):
    """
    Should be used to decorate any function that uses datacollection methods.
    """
    return needs_cache(fn, CACHE_NM, DB,
                       get_collect_name(COLLECT),
                       key_fld=OBJ_ID_NM,
                       no_id=False)


@needs_manuscripts_cache
def fetch_list():
    """
    Fetch all manuscripts: returns a list
    """
    return get_cache(COLLECT).fetch_list()


@needs_manuscripts_cache
def fetch_dict():
    return get_cache(COLLECT).fetch_dict()


@needs_manuscripts_cache
def fetch_by_key(manu_id):
    return get_cache(COLLECT).fetch_by_key(manu_id)


@needs_manuscripts_cache
def update_fld(manu_id, fld, val):
    return get_cache(COLLECT).update_fld(manu_id, fld, val, by_id=True)


def fetch_by_id(manu_id):
    return fetch_by_key(manu_id)


def get_last_updated(manu_id):
    if not exists(manu_id):
        raise ValueError(f'No such manuscript id: {manu_id}')
    return fetch_by_id(manu_id).get(LAST_UPDATED, None)


def get_state(manu_id):
    if not exists(manu_id):
        raise ValueError(f'No such manuscript id: {manu_id}')
    return fetch_by_id(manu_id).get(STATE, None)


def get_title(manu_id):
    if not exists(manu_id):
        raise ValueError(f'No such manuscript id: {manu_id}')
    return fetch_by_id(manu_id).get(TITLE, None)


def get_abstract(manu_id):
    if not exists(manu_id):
        raise ValueError(f'No such manuscript id: {manu_id}')
    return fetch_by_id(manu_id).get(ABSTRACT, None)


def get_text(manu_id):
    if not exists(manu_id):
        raise ValueError(f'No such manuscript id: {manu_id}')
    return fetch_by_id(manu_id).get(TEXT, None)


def get_authors(manu_id):
    if not exists(manu_id):
        raise ValueError(f'No such manuscript id: {manu_id}')
    return fetch_by_id(manu_id).get(AUTHORS, None)


def get_editor_email(manu_id):
    """
    In the future we may have multiple editors in a journal, and individual
    submissions may have different editors. For now, we use all the editors
    """
    editors = pqry.fetch_all_or_some(role=ED)
    return pqry.get_email(list(editors.keys())[0])


def exists(code):
    return code in fetch_dict()


TEST_CODE = 'BK'
TEST_LAST_UPDATED = tfmt.datetime_to_iso(tfmt.TEST_OLD_DATETIME)
TEST_REFEREE = 'Kris'
TEST_ABSTRACT = 'TLDR'
TEST_TEXT = 'When in the course of Boaz events ...'

TEST_MANU = {
    ABSTRACT: TEST_ABSTRACT,
    AUTHORS: [
        {
            NAME: 'Boaz Kaufman',
            EMAIL: 'boaz@donthardcorestrings.com',
        }
    ],
    CODE: TEST_CODE,
    REFEREES: {TEST_REFEREE: {}},
    TEXT_ENTRY: TEST_TEXT,
    TITLE: 'Forays into Kaufman Studies',
    WCOUNT: 500,
}

proj_dir = os.getenv('PROJ_DIR', "")
UPLOAD_DIR = f'{proj_dir}/journal_submissions'
ALLOWED_EXTENSIONS = ['txt', 'docx', 'md', 'html']


def get_valid_exts():
    return ALLOWED_EXTENSIONS


TEST_EXTENSION = 'txt'
TEST_FILENM = f'tester.{TEST_EXTENSION}'


def get_file_ext(filename):
    if '.' not in filename:
        return None
    return filename.rsplit('.', 1)[1].lower()


def is_valid_file(filename):
    return get_file_ext(filename) in get_valid_exts()


TEST_FILE_OBJ = FileStorage(filename=f'good_name.{get_valid_exts()[0]}')


def convert_file(filepath, SUBMIT_DIR):
    if get_file_ext(filepath) != 'txt':
        output = pdc.convert_file(
            filepath,
            'markdown',
            extra_args=[f'--extract-media={SUBMIT_DIR}']
        )
    else:
        with open(filepath, 'r') as f:
            output = '\n'.join(f.readlines())
    return output


def get_submission_directory(upload_dir, id):
    NEW_PATH = os.path.join(upload_dir, id)
    if os.path.exists(NEW_PATH):
        return NEW_PATH
    os.makedirs(NEW_PATH)
    return NEW_PATH


def process_file(file, SUBMIT_DIR):
    output = ''
    if file:
        filename = secure_filename(file.filename)
        if not is_valid_file(filename):
            raise ValueError('Error: valid file types are: '
                             + f'{get_valid_exts()}')
        filepath = os.path.join(SUBMIT_DIR, filename)
        file.save(filepath)
        output = convert_file(filepath, SUBMIT_DIR)
    return output, filename


def save_text_as_file(_id: str) -> dict:
    text = get_text(_id)
    SUBMIT_DIR = get_submission_directory(UPLOAD_DIR, _id)
    filename = f'{SUBMIT_DIR}/{_id}.md'
    with open(filename, 'w') as mdfile:
        mdfile.write(text)
        return (text, filename)
    raise ValueError('Could not write to file.')


def add_file(_id: str, dict_of_files: dict) -> dict:
    """
    Uploads a file to the local directory, then notifies the editor.
    """
    if not dict_of_files:
        return save_text_as_file(_id)
        # raise ValueError('Empty dict_of_files dictionary passed.')
    file_obj = None
    file_obj = dict_of_files.get(MANU_FILE, None)
    if not file_obj:
        raise ValueError('No file in dict_of_files.')
    SUBMIT_DIR = get_submission_directory(UPLOAD_DIR, _id)
    (text, filename) = process_file(file_obj, SUBMIT_DIR)
    if filename:
        os.rename(f'{SUBMIT_DIR}/{filename}',
                  f'{SUBMIT_DIR}/{_id}.{get_file_ext(filename)}')
    update(_id, {TEXT: text})
    notify_editor(_id)
    return (text, filename)


def is_file_entry(manu_data: dict) -> bool:
    return manu_data.get(MANU_FILE)


def set_manuscript_defaults(manu_data):
    manu_data[STATE] = mst.SUBMITTED
    manu_data[LAST_UPDATED] = get_curr_datetime()
    manu_data[TEXT] = manu_data.get(TEXT_ENTRY)


def add_authors(authors: list):
    for author in authors:
        pqry.possibly_new_person_add_role(
            author.get(EMAIL),
            AU,
            author.get(NAME)
        )


def add_ref_report(reports: list):
    print(REF_REPORT)
    print(REF_VERDICT)


@needs_manuscripts_cache
def add(manu_data):
    set_manuscript_defaults(manu_data)
    add_authors(manu_data[AUTHORS])
    # For testing we may add a manuscript that already has refs!
    if not manu_data.get(REFEREES):
        manu_data[REFEREES] = {}
    ret = get_cache(COLLECT).add(manu_data)
    update_history(manu_id=ret,
                   action=SUBMITTED,
                   new_state=SUBMITTED)
    return ret


@needs_manuscripts_cache
def delete(code):
    return get_cache(COLLECT).delete(code, by_id=True)


@needs_manuscripts_cache
def update(code, update_dict):
    return get_cache(COLLECT).update(code, update_dict, by_id=True)


@needs_manuscripts_cache
def fetch_by_state(state: str) -> list:
    if state not in mst.get_valid_states():
        raise ValueError(f'Invalid state: {state}.')
    return get_cache(COLLECT).fetch_by_fld_val(STATE, state)


def get_referees(manu_id: str) -> list:
    if not exists(manu_id):
        raise ValueError(f'No such manuscript id: {manu_id}')
    return fetch_by_key(manu_id).get(REFEREES, {})


def get_original_submission_filename(manu_id):
    if not exists(manu_id):
        raise ValueError(f'No such manuscript id: {manu_id}')
    SUBMIT_DIR = get_submission_directory(UPLOAD_DIR, manu_id)
    fileglob = glob.glob(f'{SUBMIT_DIR}/{manu_id}.*')
    if len(fileglob) < 1:
        return ''
    return fileglob[0]


def get_curr_datetime():
    return tfmt.datetime_to_iso(tfmt.now())


def set_last_updated(manu_id):
    curr_datetime = get_curr_datetime()
    return update_fld(manu_id, LAST_UPDATED, curr_datetime)


def set_state(manu_id, state):
    if state not in mst.get_valid_states():
        raise ValueError(f'Invalid state code {state}. \
        Valid codes are {mst.get_valid_states()}')
    return update(manu_id, {STATE: state})


REFEREE_ARG = 'referee'


def notify_referee(manu_id: str, referee: str):
    """
    When a referee is initially added, we send out an email letting them know
    that someone is asking if they can referee a manuscript. We give them the
    journal title and abstract
    """
    email = pqry.get_email(referee)
    if email is None:
        raise ValueError(f'{referee} does not have an assigned email address')
    reply_email = get_editor_email(manu_id)
    title = get_title(manu_id)
    abstract = get_abstract(manu_id)
    email_content = (f'Hello {email} you\'ve been asked to referee the '
                     f'manuscript {title}. The abstract is: <br> {abstract}')
    ret = send_mail(to_emails=email, subject='Manuscript Referee',
                    content=email_content, reply_email=reply_email)
    return ret


def notify_editor(manu_id: str):
    """
    When a manuscript is submitted, we email the editor to let them know they
    have received a new manuscipt, as well as attaching the document.
    """
    if not exists(manu_id):
        raise ValueError(f'Invalid manuscript id: {manu_id}')
    email = get_editor_email(manu_id)
    email_content = f'Hello {email}, a new manuscript has been submitted.'
    file = get_original_submission_filename(manu_id)
    if os.path.isfile(file):
        email_content += ' It has been attached to this email as a document.'
    else:
        text = get_text(manu_id)
        email_content += (' Only text was provided. It is attached here:'
                          f' {text}')
        file = None
    ret = send_mail(to_emails=email, subject='New Manuscript Submitted',
                    content=email_content, file=file)
    return ret


def assign_referee(manu_id: str, **kwargs):
    """
    Assigns a referee to a manuscript and emails them
    """
    ref_id = kwargs.get(REFEREE_ARG)
    if not ref_id:
        raise ValueError(f'Must provide \'{REFEREE_ARG}\' value to assign a '
                         'referee.')
    refs = get_referees(manu_id)
    if ref_id not in refs:
        refs[ref_id] = {}
    update_fld(manu_id, REFEREES, refs)
    ref = pqry.fetch_by_key(ref_id)
    if ref:
        pqry.add_role(ref, RE)
    notify_referee(manu_id, ref_id)
    return REFEREE_REVIEW


def remove_referee(manu_id, **kwargs):
    ref_id = kwargs.get(REFEREE_ARG)
    if not ref_id:
        raise ValueError(f'Must provide \'{REFEREE_ARG}\' value to remove a '
                         'referee.')
    refs = get_referees(manu_id)
    if ref_id not in refs:
        raise ValueError(f'Referee {ref_id} not found')
    del refs[ref_id]
    update_fld(manu_id, REFEREES, refs)
    if len(refs) == 0:
        return SUBMITTED
    else:
        return REFEREE_REVIEW


REFEREE_MODIFIED = 'referee_modified'
NEW_STATE = 'new_state'
ACTION = 'action'


def update_history(manu_id: str, action: str, new_state: str, **kwargs):
    history = fetch_by_key(manu_id).get(HISTORY, {})
    history_dict = {}
    history_dict[NEW_STATE] = new_state
    history_dict[ACTION] = action
    for key, value in kwargs.items():
        history_dict[key] = value
    history[get_curr_datetime()] = history_dict
    return update_fld(manu_id, HISTORY, history)


@needs_manuscripts_cache
def update_state(manu_id, state, referee: str = None):
    """
    Updates the history and sets all the new parameters of the manuscript.
    If state is changed to assign_referee or remove_referee the referee
    must also be provided
    """
    if state not in mst.get_valid_states():
        raise ValueError(f'Invalid state code {state}.')
    ret = set_state(manu_id, state)
    update_history(manu_id, state, referee)
    set_last_updated(manu_id)
    return ret


def editor_move(state, **kwargs):
    """
    Forcefully moves the current state to any other state.
    Currently just returns the state passed in, but we may do other things with
    it
    """
    return state


FUNC = 'function'
STATE_MAP = 'state_map'
DESTINATION = 'destination'

COMMON_ACTIONS = {EDITOR_MOVE: {
               FUNC: editor_move,
               ROLES: [ED],
               },
               WITHDRAW: {
               FUNC: lambda x, **kwargs: WITHDRAWN,
               ROLES: [AU],
               }}


STATE_TABLE = {
    AUTHOR_REVIEW: {
        DONE: {
            FUNC: lambda x, **kwargs: FORMATTING,
            ROLES: [AU],
        },
        **COMMON_ACTIONS,
    },
    AUTHOR_REVISIONS: {
        DONE: {
            FUNC: lambda x, **kwargs: EDITOR_REVIEW,
            ROLES: [AU],
        },
        **COMMON_ACTIONS,
    },
    COPY_EDITING: {
        DONE: {
            FUNC: lambda x, **kwargs: AUTHOR_REVIEW,
            ROLES: [ED],
        },
        **COMMON_ACTIONS,
    },
    EDITOR_REVIEW: {
        ACCEPT: {
            FUNC: lambda x, **kwargs: COPY_EDITING,
            ROLES: [ED],
        },
        **COMMON_ACTIONS,
    },
    FORMATTING: {
        DONE: {
            FUNC: lambda x, **kwargs: PUBLISHED,
            ROLES: [ED],
        },
        **COMMON_ACTIONS,
    },
    REFEREE_REVIEW: {
        ACCEPT: {
            FUNC: lambda x, **kwargs: COPY_EDITING,
            ROLES: [ED],
        },
        ACCEPT_W_REV: {
            FUNC: lambda x, **kwargs: AUTHOR_REVISIONS,
            ROLES: [ED],
        },
        ASSIGN_REFEREE: {
            FUNC: assign_referee,
            ROLES: [ED],
        },
        REMOVE_REFEREE: {
            FUNC: remove_referee,
            ROLES: [ED],
        },
        REJECT: {
            FUNC: lambda x, **kwargs: REJECTED,
            ROLES: [ED],
        },
        SUBMIT_REVIEW: {
            FUNC: lambda x, **kwargs: REFEREE_REVIEW,
            ROLES: [RE],
        },
        **COMMON_ACTIONS,
    },
    SUBMITTED: {
        REJECT: {
            FUNC: lambda x, **kwargs: REJECTED,
            ROLES: [ED],
        },
        ASSIGN_REFEREE: {
            FUNC: assign_referee,
            ROLES: [ED],
        },
        **COMMON_ACTIONS,
    },
}


def is_referee_for(person_id, manu_id):
    """
    Takes person_id, and manu_id and returns True if the user is a referee for
    the manuscript.
    """
    return person_id in get_referees(manu_id)


def is_author_for(person_id, manu_id):
    """
    Takes person_id and manu_id and returns True if the user is an author for
    the manuscript.
    """
    authors = get_authors(manu_id)
    email = pqry.get_email(person_id)
    for author in authors:
        if author.get(EMAIL) == email:
            return True
    return False


def is_editor_for(person_id, manu_id):
    """
    Takes person_id and manu_id and returns True if the user is an author for
    the manuscript. For now we are assuming editors have universal access.
    """
    person = pqry.fetch_by_key(person_id)
    return pqry.is_editor(person)


def get_users_role_for_manu(person_id, manu_id):
    """
    Gets the users role, returns a single string. Currently we are assuming
    that the user can only have one role per manuscript, and we fetch their
    highest role for the given manuscript.
    """
    if is_editor_for(person_id, manu_id):
        return ED
    elif is_author_for(person_id, manu_id):
        return AU
    elif is_referee_for(person_id, manu_id):
        return RE
    else:
        return None


def is_valid_action(manu_id, person_id, action):
    """
    Checks whether the given user is able to perform the provided action for
    a given manuscript, based on their roles.
    """
    user_role = get_users_role_for_manu(person_id, manu_id)
    state = get_state(manu_id)
    valid_roles = STATE_TABLE.get(state).get(action).get(ROLES)
    return user_role in valid_roles


def receive_action(manu_id, action, email: str = None, **kwargs):
    """
    Currently we have 'referee', 'state' kwargs.
    """
    if not exists(manu_id):
        raise ValueError(f'Invalid manuscript id: {manu_id}')
    if not mst.is_valid_action(action):
        raise ValueError(f'Invalid action: {action}')
    if email:
        person_id = pqry.fetch_id_by_email(email)
        if not is_valid_action(manu_id, person_id, action):
            raise ValueError(f'{email} is not allowed to perform {action}'
                             f' on {manu_id}')
    curr_state = get_state(manu_id)
    action_opts = STATE_TABLE[curr_state].get(action, {})
    func = action_opts.get(FUNC, None)
    if func:
        new_state = func(manu_id, **kwargs)
        set_state(manu_id, new_state)
        set_last_updated(manu_id)
        update_history(manu_id=manu_id,
                       action=action,
                       new_state=new_state,
                       **kwargs)
        return new_state
    else:
        raise ValueError(f'Action {action} is invalid in the current state: '
                         f'{curr_state}')


ACTIONS = 'actions'


def get_users_actions_for_manu(person_id: str, manu_id: str) -> list:
    """
    Returns a list of all the actions a user can take for a given manuscript
    """
    user_role = get_users_role_for_manu(person_id, manu_id)
    state = get_state(manu_id)
    all_actions = STATE_TABLE.get(state)
    user_actions = []
    for action, action_dict in all_actions.items():
        if user_role in action_dict.get(ROLES):
            user_actions.append(action)
    return user_actions


def fetch_manuscripts(email: str) -> dict:
    """
    Fetches manuscripts based on what the user is allowed to see
    """
    manu_dict = fetch_dict()
    person_id = pqry.fetch_id_by_email(email)
    if not person_id:
        return {}
    to_del = []
    for manu_id in manu_dict:
        actions = get_users_actions_for_manu(person_id, manu_id)
        if actions:
            manu_dict[manu_id][ACTIONS] = actions
        else:
            to_del.append(manu_id)

    for manu_id in to_del:
        del manu_dict[manu_id]
    return manu_dict


def main():
    """
    Run this as a program to see the output formats!
    """
    print("Interactive test of manuscripts data module.")
    print(f'{fetch_dict()=}')


if __name__ == '__main__':
    main()
