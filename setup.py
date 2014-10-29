try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='pymegacli',
    version='0.1.5.3',
    author='James Brown',
    author_email='jbrown@uber.com',
    url='http://github.com/uber/pymegacli',
    description='object-oriented API around the MegaCLI tool for administrating LSI RAID cards',
    license='MIT',
    classifiers=[
        'Programming Language :: Python',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
        'Topic :: System :: Hardware',
        'Topic :: System :: Monitoring',
        'Topic :: System :: Systems Administration',
        'Intended Audience :: System Administrators',
        'Development Status :: 4 - Beta',
    ],
    packages=['pymegacli'],
    scripts=['bin/check_megacli'],
    long_description=open('README.md', 'r').read(),
)
