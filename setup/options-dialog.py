#!/usr/bin/env python
# encoding: utf-8

import npyscreen
import sys
import os


class TestApp(npyscreen.NPSApp):
    def main(self):
        # These lines create the form and populate it with widgets.
        # A fairly complex screen in only 8 or so lines of code - a line for each control.
        npyscreen.setTheme(npyscreen.Themes.BlackOnWhiteTheme)

        form  = npyscreen.Form(name = "Mail-in-a-Box Options",)
        postgrey_text = form.add(
            npyscreen.TitleFixedText,
            name="POSTGREY",
            value="Should Postgrey be used to greylist messages?",
            editable=False
        )
        form.add(npyscreen.FixedText)

        postgrey_text = form.add(
            npyscreen.MultiLineEditable,
            name="POSTSRSD",
            value="The PostSRSd daemon performs return path rewriting using the SRS protocol.\n"
                  "Not that all messages, including locally delivered mail will have their return\n"
                  "paths rewritten",
            max_height=4,
            editable=False
        )
        form.add(npyscreen.FixedText)

        options = form.add(
            npyscreen.TitleMultiSelect,
            max_height=-2,
            value = [
                int(os.getenv('POSTGREY', 1)),
                int(os.getenv('POSTSRSD', 0)),
                int(os.getenv('POLICY_SPF', 0))
            ],
            name="Options",
            values= ["POSTGREY","POSTSRSD","POLICY_SPF"],
            scroll_exit=True
        )

        # This lets the user interact with the Form.
        form.edit()

        with open('_options.sh', 'w') as output:
            print('POSTGREY=%i' % (1 if 0 in options.value else 0), file=output)
            print('POSTSRSD=%i' % (1 if 1 in options.value else 0), file=output)
            print('POLICY_SPF=%i' % (1 if 2 in options.value else 0), file=output)
            # print(npyscreen.ThemeManager.default_colors, file=output)


if __name__ == "__main__":
    App = TestApp()
    App.run()
