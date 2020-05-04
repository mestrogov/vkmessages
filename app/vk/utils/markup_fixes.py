# -*- coding: utf-8 -*-

from re import sub


def markup_multipurpose_fixes(source_text):
    source_text = hts_splitting(vk_convert_links(escape_markdown(source_text)))
    return source_text.strip()


def escape_markdown(source_text):
    escape_chars = '\*_`\['

    return sub(r'([%s])' % escape_chars, r'\\\1', source_text)


def vk_convert_links(source_text):
    partitioned_text = source_text.partition('[')[-1].rpartition(']')[0]
    splitted_text = partitioned_text.split("]")
    for link in splitted_text:
        try:
            try:
                link = link.split("[")[1]
            except IndexError:
                pass
            link_splitted = link.split("|")
            replace_link = "\[" + str(link_splitted[0]) + "|" + str(link_splitted[1]) + "]"
            response_link = "[" + str(link_splitted[1]) + "](https://vk.com/" + str(link_splitted[0]) + ")"
            source_text = source_text.replace(replace_link, response_link)
        except IndexError:
            continue

    return source_text


def hts_splitting(source_text):
    splitted_text = {tag.strip("@") for tag in source_text.split() if tag.startswith("#")}
    listed_text = list(splitted_text)
    for ht_element in listed_text:
        splitted_text = ht_element.split("@")[0]
        source_text = source_text.replace(ht_element, splitted_text)

    return source_text


def escape_markdown_links(source_text):
    response_text = source_text.replace("[", "(").replace("]", ")")
    return response_text.strip()
