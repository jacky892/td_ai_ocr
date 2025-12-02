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
        "监管方式代码": "coded_attributes.trade_mode_id",
        "征免性质": "coded_attributes.levy_nature",
        "征免性质代码": "coded_attributes.levy_nature_id",
        "出境关别": "coded_attributes.customs_office",
        "出境关别代码": "coded_attributes.customs_office_id",
        "离境口岸": "coded_attributes.exit_port",
        "离境口岸代码": "coded_attributes.exit_port_id",
        "成交方式": "coded_attributes.transaction_mode",
        "成交方式代码": "coded_attributes.transaction_mode_id",
        "运输方式": "coded_attributes.transport_mode",
        "运输方式代码": "coded_attributes.transport_mode_id",
        "境内货源地": "coded_attributes.domestic_source_place",
        "境内货源地代码": "coded_attributes.domestic_source_place_id",
        "包装种类": "coded_attributes.wrapping_type",
        "包装种类代码": "coded_attributes.wrapping_type_id",

        # Logistics
        "贸易国(地区)": "logistics.trading_country",
        "贸易国(地区)代码": "logistics.trading_country_id",
        "运抵国(地区)": "logistics.destination_country",
        "运抵国(地区)代码": "logistics.destination_country_id",
        "指运港": "logistics.destination_port",
        "指运港代码": "logistics.destination_port_id",
        "运输工具名称及航次号": "logistics.transport_tool_id",
        "提运单号": "logistics.bill_of_lading_no",

        # Items (These are for the header, item-specific mappings will be different)
        "项号": "items.line_no",
        "商品编号": "items.hs_code",
        "商品名称及规格型号": "items.product_name_and_spec",
        "数量及单位": "items.quantity_and_unit",
        "单价/总价/币制": "items.price_info",
        "原产国(地区)": "items.origin_country",
        "原产国(地区)代码": "items.origin_country_id",
        "最终目的国(地区)": "items.final_destination_country",
        "最终目的国(地区)代码": "items.final_destination_country_id",
        "境内货源地": "items.domestic_source_place",
        "境内货源地代码": "items.domestic_source_place_id",
        "征免": "items.tax_mode",
        "征免代码": "items.tax_mode_id",

        # Summary
        "件数": "summary.total_packages",
        "毛重(千克)": "summary.gross_weight_kg",
        "净重(千克)": "summary.net_weight_kg",
        
        # Other
        "合同协议号": "other.contract_no",
        "备注": "other.notes",
    }
