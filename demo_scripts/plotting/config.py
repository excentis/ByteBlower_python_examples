

class Style(object):

    @classmethod
    def title(cls, title):
        styling = '<span style="font-family: \'DejaVu Sans\', Arial, Helvetica, sans-serif; color: '
        return styling + '#00AEEF; font-size: 20px; line-height: 1.2640625; ">' + title + '</span>'

    @classmethod
    def x_axis(cls, label):
        styling = '<span style="font-family: \'DejaVu Sans\', Arial, Helvetica, sans-serif; color: '
        return styling + '#F7941C; font-size: 12px; line-height: 1.4640625; font-weight: bold;">' + label + '</span>'

    @classmethod
    def y_axis(cls, label, color='#00AEEF'):
        styling = '<span style="font-family: \'DejaVu Sans\', Arial, Helvetica, sans-serif; color: ' + color + '; '
        return styling + 'line-height: 1.4640625; font-weight: bold;">' + label + '</span>'
