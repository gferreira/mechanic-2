import AppKit
import logging


logger = logging.getLogger("Mechanic")


class MCExtensionDescriptionFormatter(AppKit.NSFormatter):

    def stringForObjectValue_(self, obj):
        if obj is None or isinstance(obj, AppKit.NSNull):
            return ''
        return obj

    def attributedStringForObjectValue_withDefaultAttributes_(self, controller, attrs):
        obj = controller.extensionObject()

        attrs = dict(attrs)

        paragraph = AppKit.NSMutableParagraphStyle.alloc().init()
        paragraph.setMinimumLineHeight_(20.0)
        attrs[AppKit.NSParagraphStyleAttributeName] = paragraph

        string = AppKit.NSMutableAttributedString.alloc().initWithString_attributes_('', attrs)

        try:
            name = AppKit.NSAttributedString.alloc().initWithString_attributes_(obj.extensionName() or '', attrs)
            string.appendAttributedString_(name)

            if obj.extensionPrice():
                attrs[AppKit.NSForegroundColorAttributeName] = AppKit.NSColor.greenColor()
                price = AppKit.NSAttributedString.alloc().initWithString_attributes_('\u2003%s' % obj.extensionPrice(), attrs)
                string.appendAttributedString_(price)

            grayColor = AppKit.NSColor.colorWithCalibratedWhite_alpha_(0.6, 1)
            attrs[AppKit.NSForegroundColorAttributeName] = grayColor

            space = AppKit.NSAttributedString.alloc().initWithString_attributes_(u'\u2003', attrs)
            string.appendAttributedString_(space)

            author = AppKit.NSAttributedString.alloc().initWithString_attributes_(obj.extensionDeveloper() or '', attrs)
            string.appendAttributedString_(author)

            paragraph = AppKit.NSMutableParagraphStyle.alloc().init()
            paragraph.setLineBreakMode_(AppKit.NSLineBreakByTruncatingTail)
            paragraph.setMaximumLineHeight_(14.0)

            attrs[AppKit.NSParagraphStyleAttributeName] = paragraph
            attrs[AppKit.NSFontAttributeName] = AppKit.NSFont.systemFontOfSize_(10.0)

            cr = AppKit.NSAttributedString.alloc().initWithString_attributes_('\n', attrs)
            string.appendAttributedString_(cr)

            if obj.isExtensionInstalled() and obj.isExtensionFromStore() and obj.extensionStoreKey() is None:
                attrs[AppKit.NSForegroundColorAttributeName] = AppKit.NSColor.redColor()
                update = AppKit.NSAttributedString.alloc().initWithString_attributes_(u'Unofficial version installed ', attrs)
                string.appendAttributedString_(update)
                attrs[AppKit.NSForegroundColorAttributeName] = grayColor

            if obj.extensionNeedsUpdate():
                attrs[AppKit.NSForegroundColorAttributeName] = AppKit.NSColor.orangeColor()
                update = AppKit.NSAttributedString.alloc().initWithString_attributes_(u'Found update %s \u2192 %s\u2003' % (obj.extensionVersion(), obj.remoteVersion()), attrs)
                string.appendAttributedString_(update)
                attrs[AppKit.NSForegroundColorAttributeName] = grayColor
            elif obj.isExtensionInstalled():
                version = AppKit.NSAttributedString.alloc().initWithString_attributes_(u'%s\u2003' % obj.extensionVersion(), attrs)
                string.appendAttributedString_(version)

            description = AppKit.NSAttributedString.alloc().initWithString_attributes_(obj.extensionDescription() or u'\u2014', attrs)
            string.appendAttributedString_(description)
        except Exception as e:
            logger.error("Can not format '%s'" % obj)
            logger.error(e)

        return string

    def objectValueForString_(self, string):
        return string
