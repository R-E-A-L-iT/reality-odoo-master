# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class MailTemplate(models.Model):
    _inherit = "mail.template"

    def init(self):
        template_mail_template_data_portal_welcome = self.env.ref('portal.mail_template_data_portal_welcome')
        if template_mail_template_data_portal_welcome:
            template_mail_template_data_portal_welcome.sudo().write({
                'body_html': """
                    <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;"><tr><td align="center">
<table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;">
<tbody>
    <!-- HEADER -->
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="middle">
                    <span style="font-size: 10px;">Your Account</span><br/>
                    <span style="font-size: 20px; font-weight: bold;" t-out="object.user_id.name or ''">Marc Demo</span>
                </td><td valign="middle" align="right">
                    <img t-attf-src="/logo.png?company={{ object.user_id.company_id.id }}" style="padding: 0px; margin: 0px; height: auto; width: 80px;" t-att-alt="object.user_id.company_id.name"/>
                </td></tr>
                <tr><td colspan="2" style="text-align:center;">
                  <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin:16px 0px 16px 0px;"/>
                </td></tr>
            </table>
        </td>
    </tr>
    <!-- CONTENT -->
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="top" style="font-size: 13px;">
                    <div>
                        Dear <t t-out="object.user_id.name or ''">Marc Demo</t>,<br/> <br/>
                        Welcome to <t t-out="object.user_id.company_id.name">YourCompany</t>'s Portal!<br/><br/>
                        An account has been created for you with the following login: <t t-out="object.user_id.login">demo</t><br/><br/>
                        Click on the button below to pick a password and activate your account.
                        <div style="margin: 16px 0px 16px 0px; text-align: center;">
                            <a t-att-href="object.user_id.signup_url" style="display: inline-block; padding: 10px; text-decoration: none; font-size: 12px; background-color: #875A7B; color: #fff; border-radius: 5px;">
                                <strong>Activate Account</strong>
                            </a>
                            <a href="/web/login" style="display: inline-block; padding: 10px; text-decoration: none; font-size: 12px;">
                                <strong>Log in</strong>
                            </a>
                        </div>
                        <t t-out="object.wizard_id.welcome_message or ''">Welcome to our company's portal.</t>
                    </div>
                </td></tr>
                <tr><td style="text-align:center;">
                  <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                </td></tr>
            </table>
        </td>
    </tr>
    <!-- FOOTER -->
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; font-size: 11px; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="middle" align="left">
                    <t t-out="object.user_id.company_id.name or ''">YourCompany</t>
                </td></tr>
                <tr><td valign="middle" align="left" style="opacity: 0.7;">
                    <t t-out="object.user_id.company_id.phone or ''">+1 650-123-4567</t>
                    <t t-if="object.user_id.company_id.email">
                        | <a t-attf-href="'mailto:%s' % {{ object.user_id.company_id.email }}" style="text-decoration:none; color: #454748;" t-out="object.user_id.company_id.email or ''">info@yourcompany.com</a>
                    </t>
                    <t t-if="object.user_id.company_id.website">
                        | <a t-attf-href="'%s' % {{ object.user_id.company_id.website }}" style="text-decoration:none; color: #454748;" t-out="object.user_id.company_id.website or ''">http://www.example.com</a>
                    </t>
                </td></tr>
            </table>
        </td>
    </tr>
</tbody>
</table>
</td></tr>
</table>
                """
            })

            # commented due to Auth Signup: Reset Password is remove
#         template_reset_password_email = self.env.ref('auth_signup.reset_password_email')
#         if template_reset_password_email:
#             template_reset_password_email.sudo().write({
#                 'body_html': """
#                     <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;"><tr><td align="center">
# <table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;">
# <tbody>
#     <!-- HEADER -->
#     <tr>
#         <td align="center" style="min-width: 590px;">
#             <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
#                 <tr><td valign="middle">
#                     <span style="font-size: 10px;">Your Account</span><br/>
#                     <span style="font-size: 20px; font-weight: bold;">
#                         <t t-out="object.name or ''">Marc Demo</t>
#                     </span>
#                 </td><td valign="middle" align="right">
#                     <img t-attf-src="/logo.png?company={{ object.company_id.id }}" style="padding: 0px; margin: 0px; height: auto; width: 80px;" t-att-alt="object.company_id.name"/>
#                 </td></tr>
#                 <tr><td colspan="2" style="text-align:center;">
#                   <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
#                 </td></tr>
#             </table>
#         </td>
#     </tr>
#     <!-- CONTENT -->
#     <tr>
#         <td align="center" style="min-width: 590px;">
#             <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
#                 <tr><td valign="top" style="font-size: 13px;">
#                     <div>
#                         Dear <t t-out="object.name or ''">Marc Demo</t>,<br/><br/>
#                         A password reset was requested for the account linked to this email.
#                         You may change your password by following this link which will remain valid during 24 hours:<br/>
#                         <div style="margin: 16px 0px 16px 0px;">
#                             <a t-att-href="object.signup_url"
#                                 style="background-color: #875A7B; padding: 8px 16px 8px 16px; text-decoration: none; color: #fff; border-radius: 5px; font-size:13px;">
#                                 Change password
#                             </a>
#                         </div>
#                         If you do not expect this, you can safely ignore this email.<br/><br/>
#                         Thanks,
#                         <t t-if="user.signature">
#                             <br/>
#                             <t t-out="user.signature or ''">--<br/>Mitchell Admin</t>
#                         </t>
#                     </div>
#                 </td></tr>
#                 <tr><td style="text-align:center;">
#                   <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
#                 </td></tr>
#             </table>
#         </td>
#     </tr>
#     <!-- FOOTER -->
#     <tr>
#         <td align="center" style="min-width: 590px;">
#             <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; font-size: 11px; padding: 0px 8px 0px 8px; border-collapse:separate;">
#                 <tr><td valign="middle" align="left">
#                     <t t-out="object.company_id.name or ''">YourCompany</t>
#                 </td></tr>
#                 <tr><td valign="middle" align="left" style="opacity: 0.7;">
#                     <t t-out="object.company_id.phone or ''">+1 650-123-4567</t>
#
#                     <t t-if="object.company_id.email">
#                         | <a t-att-href="'mailto:%s' % object.company_id.email" style="text-decoration:none; color: #454748;" t-out="object.company_id.email or ''">info@yourcompany.com</a>
#                     </t>
#                     <t t-if="object.company_id.website">
#                         | <a t-att-href="'%s' % object.company_id.website" style="text-decoration:none; color: #454748;" t-out="object.company_id.website or ''">http://www.example.com</a>
#                     </t>
#                 </td></tr>
#             </table>
#         </td>
#     </tr>
# </tbody>
# </table>
# </td></tr>
# </table>
#                 """
#             })
        template_set_password_email = self.env.ref('auth_signup.set_password_email')
        template_set_password_email
        if template_set_password_email:
            template_set_password_email.sudo().write({
                'subject': """{{ object.create_uid.name }} from {{ object.company_id.name }} invites you to connect""",
                'body_html': """
                    <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;"><tr><td align="center">
<table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;">
<tbody>
    <!-- HEADER -->
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="middle">
                    <span style="font-size: 10px;">Welcome</span><br/>
                    <span style="font-size: 20px; font-weight: bold;">
                        <t t-out="object.name or ''">Marc Demo</t>
                    </span>
                </td><td valign="middle" align="right">
                    <img t-attf-src="/logo.png?company={{ object.company_id.id }}" style="padding: 0px; margin: 0px; height: auto; width: 80px;" t-att-alt="object.company_id.name"/>
                </td></tr>
                <tr><td colspan="2" style="text-align:center;">
                  <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                </td></tr>
            </table>
        </td>
    </tr>
    <!-- CONTENT -->
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="top" style="font-size: 13px;">
                    <div>
                        Dear <t t-out="object.name or ''">Marc Demo</t>,<br /><br />
                        You have been invited by <t t-out="object.company_id.name or ''">YourCompany</t> to connect.
                        <div style="margin: 16px 0px 16px 0px;">
                            <a t-att-href="object.signup_url"
                                style="background-color: #875A7B; padding: 8px 16px 8px 16px; text-decoration: none; color: #fff; border-radius: 5px; font-size:13px;">
                                Accept invitation
                            </a>
                        </div>
                        <t t-set="website_url" t-value="object.get_base_url()"></t>
                        Your URL is: <b><a t-att-href='website_url' t-out="website_url or ''">http://yourcompany.com</a></b><br />
                        Your sign in email is: <b><a t-attf-href="/web/login?login={{ object.email }}" target="_blank" t-out="object.email or ''">mark.brown23@example.com</a></b><br /><br />
                        <br /><br />
                        Enjoy!<br />
                        --<br/>The <t t-out="object.company_id.name or ''">YourCompany</t> Team
                    </div>
                </td></tr>
                <tr><td style="text-align:center;">
                  <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                </td></tr>
            </table>
        </td>
    </tr>
    <!-- FOOTER -->
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; font-size: 11px; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="middle" align="left">
                    <t t-out="object.company_id.name or ''">YourCompany</t>
                </td></tr>
                <tr><td valign="middle" align="left" style="opacity: 0.7;">
                    <t t-out="object.company_id.phone or ''">+1 650-123-4567</t>
                    <t t-if="object.company_id.email">
                        | <a t-att-href="'mailto:%s' % object.company_id.email" style="text-decoration:none; color: #454748;" t-out="object.company_id.email or ''">info@yourcompany.com</a>
                    </t>
                    <t t-if="object.company_id.website">
                        | <a t-att-href="'%s' % object.company_id.website" style="text-decoration:none; color: #454748;" t-out="object.company_id.website or ''">http://www.example.com</a>
                    </t>
                </td></tr>
            </table>
        </td>
    </tr>
</tbody>
</table>
</td></tr>
</table>
                """
            })
        template_account_created = self.env.ref('auth_signup.mail_template_user_signup_account_created')
        if template_account_created:
            template_account_created.sudo().write({
                'body_html': """
                <table border="0" cellpadding="0" cellspacing="0" style="padding-top: 16px; background-color: #F1F1F1; font-family:Verdana, Arial,sans-serif; color: #454748; width: 100%; border-collapse:separate;"><tr><td align="center">
<table border="0" cellpadding="0" cellspacing="0" width="590" style="padding: 16px; background-color: white; color: #454748; border-collapse:separate;">
<tbody>
    <!-- HEADER -->
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="middle">
                    <span style="font-size: 10px;">Your Account</span><br/>
                    <span style="font-size: 20px; font-weight: bold;">
                        <t t-out="object.name or ''">Marc Demo</t>
                    </span>
                </td><td valign="middle" align="right">
                    <img t-attf-src="/logo.png?company={{ object.company_id.id }}" style="padding: 0px; margin: 0px; height: auto; width: 80px;" t-att-alt="object.company_id.name"/>
                </td></tr>
                <tr><td colspan="2" style="text-align:center;">
                  <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                </td></tr>
            </table>
        </td>
    </tr>
    <!-- CONTENT -->
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="top" style="font-size: 13px;">
                    <div>
                        Dear <t t-out="object.name or ''">Marc Demo</t>,<br/><br/>
                        Your account has been successfully created!<br/>
                        Your login is <strong><t t-out="object.email or ''">mark.brown23@example.com</t></strong><br/>
                        To gain access to your account, you can use the following link:
                        <div style="margin: 16px 0px 16px 0px;">
                            <a t-attf-href="/web/login?auth_login={{object.email}}"
                                style="background-color: #875A7B; padding: 8px 16px 8px 16px; text-decoration: none; color: #fff; border-radius: 5px; font-size:13px;">
                                Go to My Account
                            </a>
                        </div>
                        Thanks,<br/>
                        <t t-if="user.signature">
                            <br/>
                            <t t-out="user.signature or ''">--<br/>Mitchell Admin</t>
                        </t>
                    </div>
                </td></tr>
                <tr><td style="text-align:center;">
                  <hr width="100%" style="background-color:rgb(204,204,204);border:medium none;clear:both;display:block;font-size:0px;min-height:1px;line-height:0; margin: 16px 0px 16px 0px;"/>
                </td></tr>
            </table>
        </td>
    </tr>
    <!-- FOOTER -->
    <tr>
        <td align="center" style="min-width: 590px;">
            <table border="0" cellpadding="0" cellspacing="0" width="590" style="min-width: 590px; background-color: white; font-size: 11px; padding: 0px 8px 0px 8px; border-collapse:separate;">
                <tr><td valign="middle" align="left">
                    <t t-out="object.company_id.name or ''">YourCompany</t>
                </td></tr>
                <tr><td valign="middle" align="left" style="opacity: 0.7;">
                    <t t-out="object.company_id.phone or ''">+1 650-123-4567</t>
                    <t t-if="object.company_id.email">
                        | <a t-attf-href="'mailto:%s' % {{ object.company_id.email }}" style="text-decoration:none; color: #454748;"><t t-out="object.company_id.email or ''">info@yourcompany.com</t></a>
                    </t>
                    <t t-if="object.company_id.website">
                        | <a t-attf-href="'%s' % {{ object.company_id.website }}" style="text-decoration:none; color: #454748;">
                            <t t-out="object.company_id.website or ''">http://www.example.com</t>
                        </a>
                    </t>
                </td></tr>
            </table>
        </td>
    </tr>
</tbody>
</table>
</td></tr>
</table>
                """
            })