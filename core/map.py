import simplekml
import textwrap
from markdown import markdown

class Map:
    def __init__(self, nombre, color=None, kmlcolor=None, html=True, md=True, href=None, color_to_url=None):
        self.nombre=nombre
        self.kml = simplekml.Kml()
        self.kml.document.name = self.nombre
        self.styles={}
        self.folder=None
        self.md = md
        self.html=html
        self.style=None
        self.color_to_url = color_to_url
        if color:
            self.style=self.getStyle(color, kmlcolor=kmlcolor, href=None)

    def getStyle(self, color, kmlcolor=None, href=None, mod=None):
        if kmlcolor is None:
            kmlcolor = getattr(simplekml.Color, color)
        if href is None and self.color_to_url:
            href = self.color_to_url(color, mod)
        key = (color, kmlcolor, href)
        if key not in self.styles:
            style = simplekml.Style()
            style.iconstyle.color = kmlcolor
            style.iconstyle.icon.href = href
            self.kml.document.style = style
            self.styles[key]=style
        return self.styles[key]

    def addFolder(self, name, color=None, kmlcolor=None, href=None):
        self.folder = self.kml.newfolder(name=name)
        if color:
            self.folder.style=self.getStyle(color, kmlcolor=kmlcolor, href=None)
        return self.folder

    def addPoint(self, name, lat, lon, description=None, color=None, kmlcolor=None, href=None, mod=None):
        pnt = self.folder.newpoint(name=name, coords=[(lon, lat)])
        if description:
            description = textwrap.dedent(description).strip()
            if self.md:
                description = markdown(description)
            if self.html:
                description = textwrap.dedent('''
                <![CDATA[
                <!DOCTYPE html>
                <html>
                    <body>
                        %s
                    </body>
                </html>
                ]]>
                ''').strip() % description
            pnt.description = description
        if color:
            pnt.style= self.getStyle(color, kmlcolor=kmlcolor, href=href, mod=mod)
        elif self.style:
            pnt.style = self.style
        return pnt

    def save(self, file):
        self.kml.save(file)
