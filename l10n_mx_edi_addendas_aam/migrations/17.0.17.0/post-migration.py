import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info('XXX XXX XXX XXX POST XXX XXX XXX XXX')
    _logger.info('Start script for deactivating modules of dependences')
    _logger.info(f'Version: {version}')
    cr.execute("DELETE FROM ir_module_module WHERE name ILIKE 'account_payment_widget_amount'")
    cr.execute("DELETE FROM ir_module_module WHERE name ILIKE 'html_text'")
    cr.execute("DELETE FROM ir_module_module WHERE name ILIKE 'product_supplierinfo_for_customer'")
    cr.execute("DELETE FROM ir_module_module WHERE name ILIKE 'product_tax_multicompany_default'")
    cr.execute("DELETE FROM ir_module_module WHERE name ILIKE 'purchase_discount'")
    _logger.info('Stop script for deactivating modules of dependences')
    _logger.info('XXX XXX XXX XXX POST XXX XXX XXX XXX')
