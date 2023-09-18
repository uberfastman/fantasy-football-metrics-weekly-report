from reportlab.lib.units import cm
from reportlab.platypus.doctemplate import PageTemplate, SimpleDocTemplate
from reportlab.platypus.frames import Frame
from reportlab.platypus.paragraph import Paragraph


# noinspection PyPep8Naming
class MyDocTemplate(SimpleDocTemplate):

    def __init__(self, filename, **kw):
        self.allowSplitting = 0
        SimpleDocTemplate.__init__(self, filename, **kw)
        template = PageTemplate("normal", [Frame(2.5 * cm, 2.5 * cm, 15 * cm, 25 * cm, id="F1")])
        self.addPageTemplates(template)

    # Entries to the table of contents can be done either manually by
    # calling the addEntry method on the TableOfContents object or automatically
    # by sending a "TOCEntry" notification in the afterFlowable method of
    # the DocTemplate you are using. The data to be passed to notify is a list
    # of three or four items containing a level number, the entry text, the page
    # number and an optional destination key which the entry should point to.
    # This list will usually be created in a document template's method like
    # afterFlowable(), making notification calls using the "notify()" method
    # with appropriate data.

    def afterFlowable1(self, flowable):
        """Registers TOC entries."""
        if flowable.__class__.__name__ == "Paragraph":
            text = flowable.getPlainText()
            style = flowable.style.name
            if style == "Heading1":
                self.notify("TOCEntry", (0, text, self.page))
            if style == "Heading2":
                self.notify("TOCEntry", (1, text, self.page))

    def afterFlowable2(self, flowable):
        if isinstance(flowable, Paragraph):
            txt = flowable.getPlainText()
            style = flowable.style.name
            if style == "Heading1":
                key = f"h1-{self.seq.nextf('heading1')}"
                self.canv.bookmarkPage(key)
                self.notify("TOCEntry", (0, txt, self.page))
            elif style == "Heading2":
                key = f"h2-{self.seq.nextf('heading2')}"
                self.canv.bookmarkPage(key)
                self.notify("TOCEntry", (1, txt, self.page, key))
