import math
import operator

from singleton_store import Store


def main(app):
\tbs = [b for b in app.paper.selected if b.object_type == "bond"]
\tif not len(bs) == 2:
\t\tStore.log(_("You have to have 2 bonds selected"), message_type="hint")
\t\treturn

\tb1, b2 = bs
\tcenter = set(b1.vertices) & set(b2.vertices)
\tif center:
\t\ta11 = center.pop()
\t\ta12 = b1.atom1 == a11 and b1.atom2 or b1.atom1
\t\ta22 = b2.atom1 == a11 and b2.atom2 or b2.atom1
\t\tv1 = (
\t\t\ta12.x - a11.x,
\t\t\ta12.y - a11.y,
\t\t\ta12.z - a11.z,
\t\t)
\t\tv2 = (
\t\t\ta22.x - a11.x,
\t\t\ta22.y - a11.y,
\t\t\ta22.z - a11.z,
\t\t)
\t\tprint(v1, v2)
\telse:
\t\tv1 = (
\t\t\tb1.atom1.x - b1.atom2.x,
\t\t\tb1.atom1.y - b1.atom2.y,
\t\t\tb1.atom1.z - b1.atom2.z,
\t\t)
\t\tv2 = (
\t\t\tb2.atom1.x - b2.atom2.x,
\t\t\tb2.atom1.y - b2.atom2.y,
\t\t\tb2.atom1.z - b2.atom2.z,
\t\t)

\tdot = sum(map(operator.mul, v1, v2))
\tdv1 = math.sqrt(sum(x**2 for x in v1))
\tdv2 = math.sqrt(sum(x**2 for x in v2))

\tcos_a = dot / dv1 / dv2

\tret = math.acos(cos_a)
\tprint(cos_a)

\tres = "%.2f" % (180 * ret / math.pi)

\t# draw the result
\tx = (
\t\tb1.atom1.x + b1.atom2.x + b2.atom1.x + b2.atom2.x
\t) / 4
\ty = (
\t\tb1.atom1.y + b1.atom2.y + b2.atom1.y + b2.atom2.y
\t) / 4
\tapp.paper.new_text(x, y, text=res).draw()

\tStore.log(res)
