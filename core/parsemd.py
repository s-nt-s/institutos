import re

re_key = re.compile(r"{{{([a-z0-9_\-]+)}}}", re.IGNORECASE)


def parsemd(src, dst, func):
    count_blank = 0
    with open(dst, "w") as d:
        with open(src, "r") as s:
            for l in s.readlines():
                l = re_key.sub(func, l)
                blank = not l.strip()
                if blank:
                    count_blank = count_blank + 1
                else:
                    count_blank = 0
                if not blank or count_blank < 2:
                    d.write(l)
