Experimental semantic wiki
==========================

This is a proof-of-concept semantic wiki,
storing everything (wiki text and triples) in a triple store.

Whenever the wiki text is modified, the triples are updated accordingly;
conversely,
whenever the triples are updated, the wiki text is altered accordingly.

Installing
----------

This project is written in Python,
and depends on ``rdfrest``, which is available as a part of
http://github.com/ktbs/ktbs .

``rdfrest`` and all its dependencies must be in the ``PYTHONPATH``.

Using
-----

Semwiki can be used by running ``bin/semwiki``.
Option ``--help`` provides a list of all available options.

Wiki syntax
-----------

The syntax currently supported by semwiki is very minimal:

* text within stars ``*`` is emphasized
* four dashes ``-`` or more are rendered as an horizontal rule
* a word starting with a colon ``:`` is an internal link
* a URI between angle brackets ``<>`` is an external link
* two links separated by an arrow ``->`` is a semantic link
  (of the form predicate -> object)
