#!/usr/bin/env python
# encoding: utf-8

import npyscreen
import sys
import os


class OptionsApp(npyscreen.NPSApp):
    def main(self):
        # These lines create the form and populate it with widgets.
        # A fairly complex screen in only 8 or so lines of code - a line for each control.
        npyscreen.setTheme(npyscreen.Themes.BlackOnWhiteTheme)

        form  = npyscreen.Form(name = "Mail-in-a-Box Options",)
        form.add(
            npyscreen.TitleFixedText,
            name="POSTGREY",
            value="",
            editable=False
        )
        form.add(
            npyscreen.MultiLineEdit,
            value="The Postgrey service greylists incoming messages from unknown senders.\n"
                  "It can be useful for fighting spam but often causes message delivery\n"
                  "delays of several minutes.",
            max_height=4,
            editable=False
        )

        form.add(
            npyscreen.TitleFixedText,
            name="POSTSRSD",
            value="",
            editable=False
        )
        form.add(
            npyscreen.MultiLineEdit,
            value="The PostSRSd daemon performs return path rewriting using the SRS protocol.\n"
                  "Not that all messages, including locally delivered mail will have their return\n"
                  "paths rewritten",
            max_height=4,
            editable=False
        )

        form.add(
            npyscreen.TitleFixedText,
            name="POLICY_SPF",
            value="",
            editable=False
        )
        form.add(
            npyscreen.MultiLineEdit,
            value=""
                  "The policy SPF service checks the SPF of incoming mails and rejects those\n"
                  "that do not qualify.  This helps to prevent spoofing, but if valid mail does\n"
                  "not have SPF configured properly it will be rejected.",
            max_height=4,
            editable=False
        )

        init_values = []
        if int(os.getenv('POSTGREY', 1)) == 1:
            init_values.append(0)

        if int(os.getenv('POSTSRSD', 0)) == 1:
            init_values.append(1)

        if int(os.getenv('POLICY_SPF', 0)) == 1:
            init_values.append(2)

        options = form.add(
            npyscreen.TitleMultiSelect,
            max_height=-2,
            value=init_values,
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
    App = OptionsApp()
    App.run()
