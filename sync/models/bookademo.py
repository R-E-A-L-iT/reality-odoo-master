import logging

_logger = logging.getLogger(__name__)

#class to handle the book a demo logic
class bookademo():
    _name = "bookademo"
    _description = "Class to control the book a demo logic"

    _list_of_contact = []
    _list_of_contact.append("OLIVIER@r-e-a-l.it")
    _list_of_contact.append("OLIVIER@R.Solutions")

    def __init__(self, db):
        self.db = db
        pass

    #Methode to send an email to the list of person concerned.
    def submitEmail(
        self,
        customer_name, 
        custome_phone_number, 
        customer_email, 
        company_name, 
        company_website, 
        industry_type, 
        employee_size):

        if (employee_size == 1):
            employee_size_str = "0-2"
        elif (employee_size == 2):
            employee_size_str = "3-10"
        elif (employee_size == 3):
            employee_size_str = "11-50"
        elif (employee_size == 4):
            employee_size_str = "51+"
        else:
            employee_size_str = "undeifned"

        msg =  "A customer requested a demo.\n"
        msg += "\n"
        msg += "\n"
        msg += "Customer Name: " + str(customer_name) + "\n"
        msg += "Customer Phone Number: " + str(custome_phone_number) + "\n"
        msg += "Customer Email: " + str(customer_email) + "\n"
        msg += "Company Name: " + str(company_name) + "\n"
        msg += "Company Website: " + str(company_website) + "\n"
        msg += "Industry Type: " + str(industry_type) + "\n"
        msg += "Employee size: " + employee_size_str + "\n"
        msg += "\n"
        msg += "\n"
        msg += "End of the email."

        values = {'subject': 'Book A Demo'}
        message = self.db.env['mail.message'].create(values)[0]

        values = {'mail_message_id': message.id}

        for contact_to_send_to in self._list_of_contact:
            email = self.db.env['mail.mail'].create(values)[0]
            email.body_html = msg
            email.email_to = contact_to_send_to
            email_id = {email.id}
            email.process_email_queue(email_id)            
            _logger.info(contact_to_send_to + ": " + msg)

