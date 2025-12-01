# -*- coding: utf-8 -*-

def get_trade_declaration_field_mapping():
    """
    Returns a mapping of Chinese field names to English field names
    for a trade declaration document.
    """
    return {
        # Document Info
        "预录入编号": "document_info.pre_entry_number",
        "海关编号": "document_info.customs_declaration_no",
        "申报日期": "document_info.declaration_date",
        "出口日期": "document_info.export_date",

        # Parties
        "境内发货人": "parties.consignor.name",
        "境外收货人": "parties.consignee",
        "申报单位": "parties.declaring_agent",

        # Coded Attributes
        "监管方式": "coded_attributes.trade_mode",
        "征免性质": "coded_attributes.levy_nature",
        "出境关别": "coded_attributes.customs_office",
        "离境口岸": "coded_attributes.exit_port",
        "成交方式": "coded_attributes.transaction_mode",
        "运输方式": "coded_attributes.transport_mode",
        "境内货源地": "coded_attributes.domestic_source_place",
        "包装种类": "coded_attributes.wrapping_type",

        # Logistics
        "贸易国(地区)": "logistics.trading_country",
        "运抵国(地区)": "logistics.destination_country",
        "指运港": "logistics.destination_port",
        "运输工具名称及航次号": "logistics.transport_tool_id",
        "提运单号": "logistics.bill_of_lading_no",

        # Items (These are for the header, item-specific mappings will be different)
        "项号": "items.line_no",
        "商品编号": "items.hs_code",
        "商品名称及规格型号": "items.product_name_and_spec",
        "数量及单位": "items.quantity_and_unit",
        "单价/总价/币制": "items.price_info",
        "原产国(地区)": "items.origin_country",
        "最终目的国(地区)": "items.final_destination_country",
        "征免": "items.tax_mode",

        # Summary
        "件数": "summary.total_packages",
        "毛重(千克)": "summary.gross_weight_kg",
        "净重(千克)": "summary.net_weight_kg",
        
        # Other
        "合同协议号": "other.contract_no",
        "备注": "other.notes",
    }
