"""
filter seminar xml
"""

import argparse
from functools import wraps
import inspect
import logging
from lxml import etree
import os
import re
from slugify import slugify
from statistics import mean, stdev
import sys
import traceback

DEFAULT_LOG_LEVEL = logging.WARNING
POSITIONAL_ARGUMENTS = [
    ['-l', '--loglevel', logging.getLevelName(DEFAULT_LOG_LEVEL),
        'desired logging level (' +
        'case-insensitive string: DEBUG, INFO, WARNING, or ERROR'],
    ['-v', '--verbose', False, 'verbose output (logging level == INFO)'],
    ['-w', '--veryverbose', False,
        'very verbose output (logging level == DEBUG)']
]
NS = {
    't': 'http://www.tei-c.org/ns/1.0'
}


def arglogger(func):
    """
    decorator to log argument calls to functions
    """
    @wraps(func)
    def inner(*args, **kwargs):
        logger = logging.getLogger(func.__name__)
        logger.debug("called with arguments: %s, %s" % (args, kwargs))
        return func(*args, **kwargs)
    return inner


@arglogger
def main(args):
    """
    main function
    """
    logger = logging.getLogger(sys._getframe().f_code.co_name)
    schema_doc = etree.parse('tei-epidoc.rng')
    schema = etree.RelaxNG(schema_doc)

    docs = []
    whence = os.path.realpath(args.whence)
    for root, dirs, files in os.walk(whence):
        for fn in files:
            if fn[-4:] == '.xml':
                if 'template' not in fn:
                    fpath = os.path.join(root, fn)
                    title = ': '.join(
                        fpath.partition(whence)[2][1:].split('/'))
                    try:
                        doc = etree.parse(fpath)
                    except etree.XMLSyntaxError as e:
                        logger.error('{}\n{}{}'.format(title, ' '*6, e))
                    else:
                        docs.append({
                            'title': title,
                            'doc': doc
                            })
        if '.git' in dirs:
            dirs.remove('.git')
    print('\n{}'.format('-'*80))
    print('number of well-formed files: {}'.format(len(docs)))

    # test validation
    v = 0
    for d in docs:
        if (schema.validate(d['doc'])):
            v += 1
        else:
            logger.error('{}\n{}{}'.format(title, ' '*6, 'invalid'))
    print('number of valid files: {}'.format(v))

    # number of words in div edition
    words_all = []
    words_count = []
    words_unique = []
    words_unique_count = []
    tags = []
    for d in docs:
        doc = d['doc']
        divs = doc.xpath("//t:div[@type='edition']", namespaces=NS)
        if len(divs) != 1:
            logger.error(
                '{}\n{}{}'.format(title, ' '*6, 'wrong number of divs'))
        text = etree.tostring(divs[0], method='text', encoding='UTF-8')
        words = text.split()
        words_all.extend(words)
        d['words'] = len(words)
        words_count.append(len(words))
        words = list(set([w.lower() for w in words]))
        words_unique.extend(words)
        d['words_unique'] = len(words)
        words_unique_count.append(len(words))
        descendants = divs[0].xpath('descendant::t:*', namespaces=NS)
        tags.extend([e.tag for e in descendants])

    print('total word count across all files: {}'.format(len(words_all)))
    print('mean words per edition: {}'.format(mean(words_count)))
    print('standard deviation in words per edition: {}'
          ''.format(stdev(words_count)))
    print('total unique words across all files: {}'.format(len(words_unique)))
    print('mean unique words per edition: {}'.format(mean(words_unique_count)))
    print('standard deviation in unique words per edition: {}'
          ''.format(stdev(words_unique_count)))
    tags = [t.split('}')[1] for t in tags]
    tags = sorted(list(set(tags)))
    print('tags used in editions: {}'.format(', '.join(tags)))


if __name__ == "__main__":
    log_level = DEFAULT_LOG_LEVEL
    log_level_name = logging.getLevelName(log_level)
    logging.basicConfig(level=log_level)
    try:
        parser = argparse.ArgumentParser(
            description=__doc__,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        for p in POSITIONAL_ARGUMENTS:
            d = {
                'help': p[3]
            }
            if type(p[2]) == bool:
                if p[2] is False:
                    d['action'] = 'store_true'
                    d['default'] = False
                else:
                    d['action'] = 'store_false'
                    d['default'] = True
            else:
                d['default'] = p[2]
            parser.add_argument(
                p[0],
                p[1],
                **d)
        parser.add_argument('whence', type=str, help="where to start looking")
        # example positional argument
        # parser.add_argument(
        #     'foo',
        #     metavar='N',
        #     type=str,
        #     nargs='1',
        #     help="foo is better than bar except when it isn't")
        args = parser.parse_args()
        if args.loglevel is not None:
            args_log_level = re.sub('\s+', '', args.loglevel.strip().upper())
            try:
                log_level = getattr(logging, args_log_level)
            except AttributeError:
                logging.error(
                    "command line option to set log_level failed "
                    "because '%s' is not a valid level name; using %s"
                    % (args_log_level, log_level_name))
        if args.veryverbose:
            log_level = logging.DEBUG
        elif args.verbose:
            log_level = logging.INFO
        log_level_name = logging.getLevelName(log_level)
        logging.getLogger().setLevel(log_level)
        fn_this = inspect.stack()[0][1].strip()
        title_this = __doc__.strip()
        logging.info(': '.join((fn_this, title_this)))
        if log_level != DEFAULT_LOG_LEVEL:
            logging.warning(
                "logging level changed to %s via command line option"
                % log_level_name)
        else:
            logging.info("using default logging level: %s" % log_level_name)
        logging.debug("command line: '%s'" % ' '.join(sys.argv))
        main(args)
        sys.exit(0)
    except KeyboardInterrupt as e:  # Ctrl-C
        raise e
    except SystemExit as e:  # sys.exit()
        raise e
    except Exception as e:
        print("ERROR, UNEXPECTED EXCEPTION")
        print(str(e))
        traceback.print_exc()
        os._exit(1)
