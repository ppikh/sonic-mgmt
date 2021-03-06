# This file contains the list of API's for operations on interface
# @author : Chaitanya Vella (chaitanya-vella.kumar@broadcom.com)
# @author2 :Jagadish Chatrasi (jagadish.chatrasi@broadcom.com)

import re
from collections import OrderedDict

from spytest import st

import apis.system.port as portapi
from apis.system.port_rest import rest_get_queue_counters
from apis.system.rest import config_rest, get_rest, delete_rest

from utilities.common import filter_and_select, make_list, exec_all, dicts_list_values, convert_to_bits
from utilities.utils import get_interface_number_from_name


def interface_status_show(dut, interfaces=[], cli_type=''):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """
       Author: Chaitanya Vella (chaitanya.vella-kumar@broadcom.com)
    Function to get the interface(s) status
    :param dut:
    :param interfaces:
    :param cli_type:
    :return:
    """
    if interfaces:
        interfaces = make_list(interfaces)
    if cli_type == "click":
        if interfaces:
            return portapi.get_status(dut, ','.join(interfaces), cli_type=cli_type)
        return portapi.get_status(dut, interfaces, cli_type=cli_type)
    elif cli_type == "klish":
        command = "show interface status"
        if interfaces:
            command += " | grep \"{}\"".format("|".join(interfaces))
        return st.show(dut, command, type=cli_type)
    elif cli_type in ["rest-patch", "rest-put"]:
        if interfaces:
            return portapi.get_status(dut, ','.join(interfaces), cli_type=cli_type)
        return portapi.get_status(dut, cli_type=cli_type)
    else:
        st.log("Unsupported CLI TYPE {}".format(cli_type))
        return False


def interface_operation(dut, interfaces, operation="shutdown", skip_verify=True, cli_type="", skip_error_check=False):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """
    This is an internal common function for interface operations
    Author: Chaitanya Vella (chaitanya.vella-kumar@broadcom.com)
    :param dut: dut OBJ
    :param interfaces: interfaces list
    :param operation: shutdown or startup
    :param skip_verify: to skip the verification
    :param cli_type:  (default: click)
    :return: boolean
    """
    interfaces_li = make_list(interfaces)
    if cli_type == "click":
        response = portapi.set_status(dut, interfaces_li, operation)
        if "Error" in str(response):
            st.log(response)
            return False

        if not skip_verify:
            concatd_interfaces = ",".join(interfaces_li)
            interface_list = interface_status_show(dut, concatd_interfaces)
            if operation == "shutdown":
                if interface_list[0]["oper"] != "down" and interface_list[0]["admin"] != "down":
                    st.log("Error: Interface {} is not down.".format(concatd_interfaces))
                    return False
            elif operation == "startup":
                if interface_list[0]["admin"] != "up":
                    st.log("Error: Interface {} is not up.".format(concatd_interfaces))
                    return False
        return True
    elif cli_type == "klish":
        commands = list()
        if interfaces_li:
            for intf in interfaces_li:
                intf_details = get_interface_number_from_name(intf)
                if not intf_details:
                    st.error("Interface data not found for {} ".format(intf))
                else:
                    commands.append("interface {} {}".format(intf_details["type"], intf_details["number"]))
                    command = "shutdown" if operation == "shutdown" else "no shutdown"
                    commands.append(command)
                    commands.append("exit")
        if commands:
            st.config(dut, commands, type=cli_type, skip_error_check=skip_error_check)
            return True
        return False
    elif cli_type in ["rest-patch", "rest-put"]:
        if not portapi.set_status(dut, interfaces_li, operation, cli_type=cli_type):
            return False
        if not skip_verify:
            output = interface_status_show(dut, interfaces=interfaces_li, cli_type=cli_type)
            if not output:
                st.error("No output found")
                return False
            state = 'down' if operation == 'shutdown' else 'up'
            for interface in interfaces_li:
                if filter_and_select(output, ['admin'], {'interface': interface})[0]['admin'] != state:
                    st.log("state to be validated for port: {} is: {}".format(interface, state))
                    return False
        return True
    else:
        st.log("Unsupported CLI TYPE {}".format(cli_type))
        return False


def interface_operation_parallel(input, operation='startup', thread=True, cli_type=''):
    """
    Author : Chaitanya Lohith Bollapragada
    This will perform the shutdown and noshutdown of given ports in given DUTs parallel.
    :param input: dic keys = dut, values = list of interfaces
    :param operation: shutdown | startup(default)
    :param thread:
    :return:

    Ex: interface_operation_parallel({vars:D1:[vars.D1D2P1,vars.D1D2P2], vars.D2:[vars.D2D1P1,vars.D2T1P1]},)
    """
    dut_list = input.keys()
    if not dut_list:
        return False
    cli_type = st.get_ui_type(dut_list[0], cli_type=cli_type)
    [out, exceptions] = exec_all(thread, [[interface_operation, dut, input[dut], operation, True, cli_type]
                                          for dut in dut_list])
    st.log(exceptions)
    return False if False in out else True


def interface_shutdown(dut, interfaces, skip_verify=True, cli_type="", skip_error_check=False):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """
      Function to shutdown interface
    Author: Chaitanya Vella (chaitanya.vella-kumar@broadcom.com)
    :param dut:
    :param interfaces:
    :param skip_verify:
    :param cli_type:
    :return:
    """
    return interface_operation(dut, interfaces, "shutdown", skip_verify, cli_type=cli_type, skip_error_check=skip_error_check)


def interface_noshutdown(dut, interfaces, skip_verify=True, cli_type=''):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """
      Function to no shut the interface
    Author: Chaitanya Vella (chaitanya.vella-kumar@broadcom.com)
    :param dut:
    :param interfaces:
    :param skip_verify:
    :param cli_type:
    :return:
    """
    return interface_operation(dut, interfaces, "startup", skip_verify, cli_type=cli_type)


def interface_properties_set(dut, interfaces_list, property, value, skip_error=False, no_form=False, cli_type=''):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """
        Function to set the interface properties.
    Author: Chaitanya Vella (chaitanya.vella-kumar@broadcom.com)
    :param dut:
    :param interfaces_list:
    :param property:
    :param value:
    :param skip_error:
    :param no_form:
    :param cli_type:
    :return:
    """
    interfaces_li = list(interfaces_list) if isinstance(interfaces_list, list) else [interfaces_list]
    if cli_type == "click":
        for each_interface in interfaces_li:
            if property.lower() == "speed":
                command = "config interface speed {} {}".format(each_interface, value)
                if skip_error:
                    try:
                        st.config(dut, command)
                    except Exception as e:
                        st.log(e)
                        st.log("Error handled by API..")
                        return False
                else:
                    st.config(dut, command)
            elif property.lower() == "fec":
                if value not in ["rs", "fc", "none"]:
                    st.log("Provided fec value not supported ...")
                    return False
                command = "config interface fec {} {}".format(each_interface, value)
                st.config(dut, command)
            elif property.lower() == "mtu":
                command = "config interface mtu {} {}".format(each_interface, value)
                out = st.config(dut, command, skip_error_check=skip_error)
                if re.search(r'Error: Interface MTU is invalid.*', out):
                    return False
            else:
                st.log("Invalid property '{}' used.".format(property))
                return False
        return True
    elif cli_type == "klish":
        properties = {"mtu": "mtu", "description": "description", "ip_address": "ip address",
                      "ipv6_address": "ipv6 address", "speed": "speed", "autoneg": "autoneg"}
        commands = list()
        for interface in interfaces_li:
            intf_details = get_interface_number_from_name(interface)
            if not intf_details:
                st.log("Interface data not found for {} ".format(interface))
            commands.append("interface {} {}".format(intf_details["type"], intf_details["number"]))
            if not no_form:
                if property.lower() == "autoneg":
                    command = "autoneg on"
                elif property.lower() == "fec":
                    if value not in ["rs", "fc", "none"]:
                        st.log("Provided fec value not supported ...")
                        return False
                    if value != "none":
                        command = " fec {}".format(value.upper())
                    else:
                        command = " fec off"
                else:
                    command = "{} {}".format(properties[property.lower()], value)
                commands.append(command)
            else:
                if property.lower() == "autoneg":
                    command = "autoneg off"
                elif property.lower() in ["ip_address", "ipv6_address"]:
                    command = "no {} {}".format(properties[property.lower()], value)
                elif property.lower() == "fec":
                    command = "no fec"
                else:
                    command = "no {}".format(properties[property.lower()])
                commands.append(command)
            commands.append("exit")
            if commands:
                st.config(dut, commands, type=cli_type)
        return True
    elif cli_type in ["rest-patch", "rest-put"]:
        rest_urls = st.get_datastore(dut, "rest_urls")
        for interface in interfaces_li:
            if property.lower() == "mtu":
                url = rest_urls['per_interface_config'].format(interface)
                if not no_form:
                    mtu_config = {"openconfig-interfaces:config": {"mtu": int(value)}}
                    if not config_rest(dut, http_method=cli_type, rest_url=url, json_data=mtu_config):
                        return False
                else:
                    mtu_config = {"openconfig-interfaces:config": {"mtu": 9100}}
                    if not config_rest(dut, http_method=cli_type, rest_url=url, json_data=mtu_config):
                        return False
            elif property.lower() == "description":
                url = rest_urls['per_interface_config'].format(interface)
                if not no_form:
                    description_config = {"openconfig-interfaces:config": {"description": value}}
                    if not config_rest(dut, http_method=cli_type, rest_url=url, json_data=description_config):
                        return False
                else:
                    description_config = {"openconfig-interfaces:config": {"description": ""}}
                    if not config_rest(dut, http_method=cli_type, rest_url=url, json_data=description_config):
                        return False
            elif property.lower() == "fec":
                url = rest_urls['fec_config_unconfig'].format(interface)
                if value not in ["rs", "fc", "none"]:
                    st.log("Provided fec value not supported ...")
                    return False
                if not no_form:
                    if value == "rs":
                        fec_config = {"openconfig-if-ethernet-ext2:port-fec": "FEC_RS"}
                        if not config_rest(dut, http_method=cli_type, rest_url=url, json_data=fec_config):
                            return False
                    if value == "fc":
                        fec_config = {"openconfig-if-ethernet-ext2:port-fec": "FEC_FC"}
                        if not config_rest(dut, http_method=cli_type, rest_url=url, json_data=fec_config):
                            return False
                    if value == "none":
                        fec_config = {"openconfig-if-ethernet-ext2:port-fec": "FEC_DISABLED"}
                        if not config_rest(dut, http_method=cli_type, rest_url=url, json_data=fec_config):
                            return False
                else:
                    if not delete_rest(dut, rest_url=url):
                        return False

            else:
                st.error("Invalid property:{}".format(property))
                return False
        return True
    else:
        st.log("Unsupported CLI TYPE {}".format(cli_type))
        return False


def _get_interfaces_by_status(dut, status, cli_type=""):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """
    Internal function to get the interface status
    Author: Chaitanya Vella (chaitanya.vella-kumar@broadcom.com)
    :param dut: dut obj
    :param status: status of the interface
    :return: list of interface status
    """
    output = interface_status_show(dut, cli_type=cli_type)
    retval = []
    match = {"oper": status} if status else None
    entries = filter_and_select(output, ["interface"], match)
    for ent in entries:
        retval.append(ent["interface"])
    return retval


def get_up_interfaces(dut, cli_type=""):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """
    Author: Chaitanya Vella (chaitanya.vella-kumar@broadcom.com)
    This is to get the list of up interfaces
    :param dut: dut obj
    :return: list of interfaces
    """
    return _get_interfaces_by_status(dut, "up", cli_type=cli_type)


def get_down_interfaces(dut, cli_type=""):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """
    Author: Chaitanya Vella (chaitanya.vella-kumar@broadcom.com)
    :param dut: DUT object
    :return: list of down interfaces
    """
    return _get_interfaces_by_status(dut, "down", cli_type=cli_type)


def get_all_interfaces(dut, int_type=None, cli_type=""):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """
    Author: Chaitanya Vella (chaitanya.vella-kumar@broadcom.com)
    API to get all the interfaces nin DUT
    :param dut: dut object
    :param int_type: physical | port_channel
    :param cli_type:
    :return: interface list
    """
    output = interface_status_show(dut, cli_type=cli_type)
    out = dicts_list_values(output, 'interface')
    if out:
        if int_type == 'physical':
            return [each for each in out if each.startswith("Eth")]
        elif int_type == 'port_channel':
            return [each for each in out if each.lower().startswith("portchannel")]
        else:
            return out
    else:
        return []


def get_all_ports_speed_dict(dut, cli_type=""):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """
    :param dut:
    :return: dict of all ports of same speed
    """
    all_speed_ports = dict()
    output = interface_status_show(dut, cli_type=cli_type)
    physical_port_list = [each['interface'] for each in output if each['interface'].startswith("Eth")]
    for each in physical_port_list:
        speed = filter_and_select(output, ['speed'], {'interface': each})[0]['speed']
        if speed not in all_speed_ports:
            all_speed_ports[speed] = [each]
        else:
            all_speed_ports[speed].append(each)
    return all_speed_ports


def verify_interface_status(dut, interface, property, value, cli_type=""):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """
    Author: Chaitanya Vella (chaitanya.vella-kumar@broadcom.com)
    This API to verify the interface status
    :param dut: dut obj
    :param interface: Interface Name
    :param property: Interface property
    :param value: Property Value
    :param cli_type:
    :return: Boolean
    """
    interface_list = make_list(interface)
    is_found = 1
    for port in interface_list:
        interface_details = interface_status_show(dut, port, cli_type=cli_type)
        match = {"interface": port, property: value}
        entries = filter_and_select(interface_details, ["interface"], match)
        if not bool(entries):
            is_found = 0
            break
        else:
            is_found = 1
    if not is_found:
        return False
    return True


def clear_interface_counters(dut, **kwargs):
    cli_type = st.get_ui_type(dut, **kwargs)
    interface_name = kwargs.get("interface_name", "")
    interface_type = kwargs.get("interface_type", "all")
    if cli_type == "klish":
        confirm = kwargs.get("confirm") if kwargs.get("confirm") else "y"
        if interface_type != "all":
            interface_type = get_interface_number_from_name(str(interface_name))
            if interface_type["type"] and interface_type["number"]:
                interface_val = "{} {}".format(interface_type.get("type"), interface_type.get("number"))
            else:
                interface_val = ""
        else:
            interface_val = "all"
        if not interface_val:
            st.log("Invalid interface type")
            return False
        command = "clear counters interface {}".format(interface_val)
        st.config(dut, command, type=cli_type, confirm=confirm, conf=False, skip_error_check=True)
    elif cli_type == "click":
        command = "show interfaces counters -c"
        if not st.is_feature_supported("show-interfaces-counters-clear-command", dut):
            st.community_unsupported(command, dut)
            return st.config(dut, "sonic-clear counters")
        return st.show(dut, command)
    elif cli_type in ["rest-patch", "rest-put"]:
        rest_urls = st.get_datastore(dut, "rest_urls")
        url = rest_urls['clear_interface_counters']
        clear_type = 'all' if interface_type == 'all' else interface_name
        clear_counters = {"sonic-interface:input": {"interface-param": clear_type}}
        if not config_rest(dut, http_method='post', rest_url=url, json_data=clear_counters, timeout=50):
            st.error("Failed to clear interface counters")
            return False
    else:
        st.log("Unsupported CLI TYPE {}".format(cli_type))
        return False
    return True


def show_interfaces_counters(dut, interface=None, property=None, cli_type=""):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """
    show interface counter
    Author : Prudvi Mangadu (prudvi.mangadu@broadcom.com)
    :param dut:
    :param interface:
    :param property:
    :param cli_type:
    :return:
    """
    if cli_type == "click":
        command = 'show interfaces counters'
        output = st.show(dut, command)
        if interface:
            if property:
                output = filter_and_select(output, [property], {'iface': interface})
            else:
                output = filter_and_select(output, None, {'iface': interface})
        return output
    elif cli_type == "klish":
        command = "show interface counters"
        if interface:
            command += " | grep \"{}\"".format("|".join(make_list(interface)))
        return st.show(dut, command, type=cli_type)
    elif cli_type in ["rest-patch", "rest-put"]:
        result = portapi.get_interface_counters_all(dut, cli_type=cli_type)
        if interface:
            if property:
                result = filter_and_select(result, [property], {'iface': interface})
            else:
                result = filter_and_select(result, None, {'iface': interface})
        return result
    else:
        st.log("Unsupported CLI TYPE {}".format(cli_type))
        return False


def show_interface_counters_all(dut, cli_type=''):
    """
    Show interface counter all.
    Author : Prudvi Mangadu (prudvi.mangadu@broadcom.com)
    :param dut:
    :return:
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    if cli_type == 'click':
        command = "show interfaces counters -a"
        return st.show(dut, command, type=cli_type)
    elif cli_type == 'klish':
        command = "show interface counters"
        return st.show(dut, command, type=cli_type)
    elif cli_type in ["rest-patch", "rest-put"]:
        return portapi.get_interface_counters_all(dut, cli_type=cli_type)
    else:
        st.error('Invalid CLI type')
        return False


def get_interface_counters(dut, port, *counter, **kwargs):
    """
    This API is used to get the interface counters.
    Author : Prudvi Mangadu (prudvi.mangadu@broadcom.com)
    :param dut:
    :param port:
    :param counter:
    :return:
    """
    cli_type = kwargs.pop('cli_type', st.get_ui_type(dut,**kwargs))
    output = show_specific_interface_counters(dut, port, cli_type=cli_type)
    entries = filter_and_select(output, counter, {'iface': port})
    return entries


def show_specific_interface_counters(dut, interface_name,  cli_type=''):
    """
    API to fetch the specific interface counters
    :param dut:
    :param interface_name:
    :return:
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    if cli_type == 'click':
        command = "show interfaces counters -a -i {}".format(interface_name)
        if not st.is_feature_supported("show-interfaces-counters-interface-command", dut):
            st.community_unsupported(command, dut)
            command = "show interfaces counters -a | grep -w {}".format(interface_name)
        output = st.show(dut, command)
    elif cli_type == 'klish':
        command = "show interface counters | grep \"{} \"".format(interface_name)
        output = st.show(dut, command, type=cli_type)
    elif cli_type in ["rest-patch", "rest-put"]:
        rest_urls = st.get_datastore(dut, "rest_urls")
        url = rest_urls['per_interface_details'].format(interface_name)
        output = []
        result = get_rest(dut, rest_url = url, timeout=60)
        processed_output = portapi.process_intf_counters_rest_output(result)
        if processed_output:
            output.extend(processed_output)
    st.log(output)
    return output


def poll_for_interfaces(dut, iteration_count=180, delay=1, cli_type=""):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """
    This API is to  poll the DUT to get the list of interfaces
    Author: Chaitanya Vella (chaitanya.vella-kumar@broadcom.com)
    :param dut:
    :param iteration_count:
    :param delay:
    :param cli_type:
    :return:
    """
    i = 1
    while True:
        intefaces_list = get_all_interfaces(dut, cli_type=cli_type)
        if intefaces_list:
            st.log("Interfaces list found ...")
            return True
        if i > iteration_count:
            st.log("Max {} tries Exceeded. Exiting ..".format(i))
            return False
        i += 1
        st.wait(delay)


def poll_for_interface_status(dut, interface, property, value, iteration=5, delay=1, cli_type=""):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """
    API to poll for interface status
    Author: Chaitanya Vella (chaitanya.vella-kumar@broadcom.com)
    :param dut:
    :param interface:
    :param property:
    :param value:
    :param iteration:
    :param delay:
    :param cli_type:
    :return:
    """
    i = 1
    while True:
        if verify_interface_status(dut, interface, property, value, cli_type=cli_type):
            st.log("Observed interface status match at {} iteration".format(i))
            return True
        if i > iteration:
            st.log("Max iterations {} reached".format(i))
            return False
        i += 1
        st.wait(delay)


def get_interface_property(dut, interfaces_list, property, cli_type=""):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """

    :param dut:
    :param interfaces_list: API accepts interfaces list or single interface
    :param property: single property need to provide
    :param cli_type:
    :return: Returns interfaces list properties in the interfaces order passed to api
    """
    interfaces_li = make_list(interfaces_list)
    output = interface_status_show(dut, interfaces_li, cli_type=cli_type)
    return_list = []
    for each_interface in interfaces_li:
        property_val = filter_and_select(output, [property], {'interface': each_interface})
        if not property_val:
            break
        return_list.append(property_val[0][property])
    return return_list


def config_static_ip_to_interface(dut, interface_name, ip_address, netmask, gateway):
    """
    API to configure static ip address to an interface
    Author: Chaitanya Vella (chaitanya.vella-kumar@broadcom.com)
    :param dut:
    :param interface_name:
    :param ip_address:
    :param netmask:
    :param gateway:
    :return:
    """
    command = "ifconfig {} {} netmask {}".format(interface_name, ip_address, netmask)
    st.config(dut, command)
    command = 'ip route add default via {}'.format(gateway)
    st.config(dut, command)


def delete_ip_on_interface_linux(dut, interface_name, ip_address):
    """
    :param dut:
    :param interface_name:
    :param ip_address:
    :return:
    """
    command = "ip addr del {} dev {}".format(ip_address, interface_name)
    st.config(dut, command)


def show_queue_counters(dut, interface_name, queue=None, cli_type=''):
    """
    Show Queue counters
    Author : Prudvi Mangadu (prudvi.mangadu@broadcom.com)
    :param dut:
    :param interface_name:
    :param queue: UC0-UC9 | MC10-MC19 (Default None)
    :return:
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    if cli_type == 'click':
        command = "show queue counters {}".format(interface_name)
        output = st.show(dut, command, type=cli_type)
    elif cli_type == 'klish':
        if interface_name == "CPU":
            command = "show queue counters interface CPU"
        else:
            intf_details = get_interface_number_from_name(interface_name)
            command = "show queue counters interface {} {}".format(intf_details['type'], intf_details['number'])
        output = st.show(dut, command, type=cli_type)
    elif cli_type in ['rest-patch', 'rest-put']:
        output = rest_get_queue_counters(dut, interface_name)
    else:
        st.log("Unsupported CLI TYPE {}".format(cli_type))
        return False
    if queue:
        return filter_and_select(output, None, {'txq': queue})
    return output


def clear_queue_counters(dut, interfaces_list=[], cli_type=''):
    """
    Clear Queue counters
    Author : Prudvi Mangadu (prudvi.mangadu@broadcom.com)
    :param dut:
    :return:
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    if cli_type in ['rest-put', 'rest-patch']:     #OC-YANG URL is not available to clear counters, reported JIRA: SONIC-23227 for this.
        cli_type = 'klish'
    if cli_type == 'click':
        interface_li = make_list(interfaces_list)
        if not interface_li:
            command = "show queue counters -c"
            st.show(dut, command)
        else:
            for each_port in interface_li:
                command = "show queue counters {} -c".format(each_port)
                st.show(dut, command, type=cli_type)
    elif cli_type == 'klish':
        if interfaces_list:
            port_list = make_list(interfaces_list)
            for port in port_list:
                if port == "CPU":
                    command = "clear queue counters interface CPU"
                else:
                    intf_details = get_interface_number_from_name(port)
                    command = 'clear queue counters interface {} {}'.format(intf_details['type'], intf_details['number'])
                st.config(dut, command, type=cli_type)
        else:
            command = 'clear queue counters'
            st.config(dut, command, type=cli_type)
    else:
        st.log("Unsupported CLI TYPE {}".format(cli_type))
        return False
    return True


def get_free_ports_speed_dict(dut, cli_type=""):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """
    :param dut:
    :param cli_type:
    :return: dict of free ports of same speed
    """
    free_speed_ports = dict()
    free_ports = st.get_free_ports(dut)
    output = interface_status_show(dut, cli_type=cli_type)
    for each in free_ports:
        speed = filter_and_select(output, ['speed'], {'interface': each})[0]['speed']
        if speed not in free_speed_ports:
            free_speed_ports[speed] = [each]
        else:
            free_speed_ports[speed].append(each)
    return free_speed_ports


def enable_dhcp_on_interface(dut, interface_name, type="v4", skip_error_check=False):
    """
    :param dut:
    :param interface_name:
    :return:
    """
    version = ""
    if type == "v6":
        version = "-6"
    command = "dhclient {} {}".format(version, interface_name)
    return st.config(dut, command, skip_error_check=skip_error_check)


def show_interface_counters_detailed(dut, interface, filter_key=None, cli_type=""):
    """
    show interfaces counters detailed <interface>.
    Author : Rakesh Kumar Vooturi (rakesh-kumar.vooturi@broadcom.com)
    :param dut:
    :param interface:
    :return:
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    cli_type = "klish" if cli_type in ["rest-put", "rest-patch"] else cli_type
    intf_details = get_interface_number_from_name(interface)
    intf_type = intf_details['type']
    ## Adding this logic due to defect SONIC-28659 will revert back once it is fixed
    if intf_type == "PortChannel":
        cli_type = "click"
    if cli_type == "click":
        command = "show interfaces counters detailed {}".format(interface)
    else:
        command = "show interface counters {}".format(interface)
    if not st.is_feature_supported("show-interfaces-counters-detailed-command", dut):
        st.community_unsupported(command, dut)
        output = st.show(dut, command, skip_error_check=True)
    else:
        output = st.show(dut, command, type=cli_type)
    if not filter_key:
        return output
    else:
        if not output:
            return False
        return output[0][filter_key]


def clear_watermark_counters(dut, mode='all'):
    """
    Clear  Watermark counters
    Author : Prudvi Mangadu (prudvi.mangadu@broadcom.com)
    :param dut:
    :param mode:
    :return:
    """
    if mode == 'multicast' or mode == 'all':
        command = "sonic-clear queue watermark multicast"
        st.config(dut, command)
    if mode == 'unicast' or mode == 'all':
        command = "sonic-clear queue watermark unicast"
        st.config(dut, command)
    if mode == 'shared' or mode == 'all':
        command = "sonic-clear priority-group watermark shared"
        st.config(dut, command)
    if mode == 'headroom' or mode == 'all':
        command = "sonic-clear priority-group watermark headroom"
        st.config(dut, command)
    return True


def show_watermark_counters(dut, mode='all'):
    """
    Show Watermark counters
    Author : Prudvi Mangadu (prudvi.mangadu@broadcom.com)
    :param dut:
    :param mode:
    :return:
    """
    result = ''
    if mode == 'multicast' or mode == 'all':
        command = "show queue watermark multicast"
        result += st.show(dut, command, skip_tmpl=True)
    if mode == 'unicast' or mode == 'all':
        command = "show queue watermark unicast"
        result += st.show(dut, command, skip_tmpl=True)
    if mode == 'shared' or mode == 'all':
        command = "show priority-group watermark shared"
        result += st.show(dut, command, skip_tmpl=True)
    if mode == 'headroom' or mode == 'all':
        command = "show priority-group watermark headroom"
        result += st.show(dut, command, skip_tmpl=True)
    return result


def get_interface_counter_value(dut, ports, properties, cli_type=""):
    """
    This API is used to get the multiple interfaces counters value in dictionary of dictionaries.
    Author : Ramprakash Reddy (ramprakash-reddy.kanala@broadcom.com)
    :param dut:
    :param ports: Interfaces names ["Ethernet0","Ethernet1"]
    :param property: Interface properties ["rx_ok","tx_ok"]
    :return: {"Ethernet0":{"rx_ok":"1234","tx_ok":"45"},"Ethenrnet1":{"rx_ok"="4325","tx_ok"="2424"}}
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    if not isinstance(ports, list):
        ports = [ports]
    if not isinstance(properties, list):
        properties = [properties]
    counters_dict = dict()
    output = show_interface_counters_all(dut, cli_type=cli_type)
    for each_port in ports:
        entries = filter_and_select(output, properties, {'iface': each_port})[0]
        counters_dict[each_port] = entries
    return convert_to_bits(counters_dict)


def verify_interface_counters(dut, params, cli_type=""):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """
    :param dut:
    :param params: {"module_type":"mirror","source":["Ethernet1","tx_ok"], "destination":["Ethernet2","rx_ok"],
    "mirrored_port":["Ethernet3","rx_ok"]}
    :param cli_type:
    :return:
    """
    st.log("Verifying interface counters on {}".format(dut))
    output = show_interface_counters_all(dut, cli_type=cli_type)
    if not output:
        st.log("Output not found")
        return False
    if params:
        source_counters, destination_counters, mirror_counters = 0, 0, 0
        module_type = params.get("module_type", "mirror")
        for data in output:
            if params.get("source") and data["iface"] == params["source"][0]:
                source_counters = data[params["source"][1]]
            if params.get("destination") and data["iface"] == params["destination"][0]:
                destination_counters = data[params["destination"][1]]
            if module_type in ["mirror", "mirror_both"] and params.get("mirrored_port"):
                if data["iface"] == params["mirrored_port"][0]:
                    mirror_counters = \
                        data[params["mirrored_port"][1]]
        try:
            st.log('The source counter is {}'.format(source_counters))
            st.log('The destination counter is {}'.format(destination_counters))
            st.log("Mirror Counters:{}".format(mirror_counters))
            float(source_counters.split()[0].replace(",", ""))
            float(destination_counters.split()[0].replace(",", ""))
        except Exception:
            st.report_fail("counters_are_not_initilaized")
        source_counters = int(source_counters.replace(",", ""))
        destination_counters = int(destination_counters.replace(",", ""))
        mirror_counters = int(mirror_counters.replace(",", ""))
        if module_type == "mirror":
            if not ((mirror_counters >= 0.93 * source_counters) and (destination_counters >= 0.93 * source_counters)):
                st.log("Counters mismatch Source Counters:{},Destination Counters:{}Mirror"
                       " Counters:{}".format(source_counters, destination_counters, mirror_counters))
                st.log("Observed mismatch in counter validation")
                st.log("Source Counters:{}".format(source_counters))
                st.log("Destination Counters:{}".format(destination_counters))
                st.log("Mirror Counters:{}".format(mirror_counters))
                return False
            else:
                return True
        elif module_type == "mirror_both":
            mirror_counters_both = int(source_counters) + int(destination_counters)
            #mirror_counters_both = int(mirror_counters_both.replace(",", ""))
            if not (int(mirror_counters) >= 0.93 * mirror_counters_both):
                st.log("Observed mismatch in counter validation")
                st.log("Source Counters:{}".format(source_counters))
                st.log("Destination Counters:{}".format(destination_counters))
                st.log("Mirror Counters:{}".format(mirror_counters))
                st.log("Mirror Counters both:{}".format(mirror_counters_both))
                return False
            else:
                return True
        elif module_type == "bum":
            source_counters = int(round(float(source_counters.split()[0])))
            destination_counters = int(round(float(destination_counters.split()[0])))
            if not destination_counters - source_counters <= 100:
                st.log("Destination counter:{} and Source Counters:{}".format(destination_counters,
                                                                              source_counters))
                return False
            else:
                return destination_counters
        else:
            st.log("Unsupported module type {}".format(module_type))
            return False
    else:
        st.log("Parameters not found - {} ...".format(params))
        return False


def config_portchannel_interfaces(dut, portchannel_data={}, config='yes', cli_type=''):

    if config == 'yes' or config == 'add':
        config = 'add'
    elif config == 'no' or config == 'del':
        config = 'del'
    else :
        st.error("Invalid config type {}".format(config))
        return False

    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    command = []

    if config == 'del' :
        for if_name, if_data in portchannel_data.items():
            pch_info = get_interface_number_from_name(if_name)
            for link_member in if_data['members'] :
                if cli_type == 'click':
                    cmd_str = "sudo config portchannel member {} {} {} ".format(config, if_name, link_member)
                    command.append(cmd_str)
                elif cli_type == 'klish':
                    intf_info = get_interface_number_from_name(link_member)
                    cmd_str = "interface {} {}".format(intf_info["type"], intf_info["number"])
                    command.append(cmd_str)
                    cmd_str = "no channel-group"
                    command.append(cmd_str)
                    command.append('exit')

        if cli_type in ['click', 'klish'] :
            try:
                st.config(dut, command, type=cli_type)
            except Exception as e:
                st.log(e)
                return False

    command = []
    for if_name, if_data in portchannel_data.items():
        if cli_type == 'click':
            cmd_str = "sudo config portchannel {} {}  ".format(config, if_name)
            command.append(cmd_str)
        elif cli_type == 'klish':
            pch_info = get_interface_number_from_name(if_name)
            cmd_str = 'no ' if config == 'del' else ''
            cmd_str += "interface {} {}".format(pch_info["type"], pch_info["number"])
            command.append(cmd_str)
            if config == 'add' :
                command.append('no shutdown')
                command.append('exit')

    if cli_type in ['click', 'klish'] :
        try:
            st.config(dut, command, type=cli_type)
        except Exception as e:
            st.log(e)
            return False

    command = []
    if config == 'add' :
        for if_name, if_data in portchannel_data.items():
            pch_info = get_interface_number_from_name(if_name)

            for link_member in if_data['members'] :
                if cli_type == 'click':
                    cmd_str = "sudo config portchannel member {} {} {} ".format(config, if_name, link_member)
                    command.append(cmd_str)
                elif cli_type == 'klish':
                    intf_info = get_interface_number_from_name(link_member)
                    cmd_str = "interface {} {}".format(intf_info["type"], intf_info["number"])
                    command.append(cmd_str)
                    cmd_str = "channel-group {}".format(pch_info["number"])
                    command.append(cmd_str)
                    command.append('exit')

                    intf_info = get_interface_number_from_name(link_member)
                    cmd_str = "interface {} {}".format(intf_info["type"], intf_info["number"])
                    command.append(cmd_str)

        if cli_type in ['click', 'klish'] :
            try:
                st.config(dut, command, type=cli_type)
            except Exception as e:
                st.log(e)
                return False

    return True


def config_vlan_interfaces(dut, vlan_data={}, config='yes', skip_error=False, cli_type=''):

    if config == 'yes' or config == 'add':
        config = 'add'
    elif config == 'no' or config == 'del':
        config = 'del'
    else :
        st.error("Invalid config type {}".format(config))
        return False

    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    command = []
    if config == 'del' :
        for _, if_data in vlan_data.items():
            vlan_id = if_data['vlan_id']

            range_cmd = False
            if 'range' in if_data.keys():
                range_ids = if_data['range']
                if range_ids[0] < range_ids[1] :
                    range_min, range_max = range_ids[0], range_ids[1]
                    range_cmd = True
                elif range_ids[0] > range_ids[1] :
                    range_min, range_max = range_ids[1], range_ids[0]
                    range_cmd = True
                else :
                    vlan_id = range_ids[0]

            for link_member in if_data['members'] :

                if cli_type == 'klish':
                    intf_info = get_interface_number_from_name(link_member)
                    cmd_str = 'interface {} {}'.format(intf_info["type"], intf_info["number"])
                    command.append(cmd_str)

                if not range_cmd :
                    if cli_type == 'click':
                        cmd_str = "config vlan member {} {} {} ".format(config, vlan_id, link_member)
                        command.append(cmd_str)
                    elif cli_type == 'klish':
                        cmd_str = "no switchport trunk allowed Vlan {}".format(vlan_id)
                        command.append(cmd_str)
                elif st.is_feature_supported("vlan-range", dut):
                    if cli_type == 'click':
                        cmd_str = "config vlan member range {} {} {} {}".format(config, range_min, range_max, link_member)
                        command.append(cmd_str)
                    elif cli_type == 'klish':
                        cmd_str = "no switchport trunk allowed Vlan {}-{}".format(range_min, range_max)
                        command.append(cmd_str)
                else:
                    skip_error = True
                    for vid in range(range_min, range_max+1):
                        if cli_type == 'click':
                            cmd_str = "config vlan member {} {} {} ".format(config, vid, link_member)
                            command.append(cmd_str)
                        elif cli_type == 'klish':
                            cmd_str = "no switchport trunk allowed Vlan {}".format(vid)
                            command.append(cmd_str)

                if cli_type == 'klish':
                     command.append('exit')


        if cli_type in ['click', 'klish'] :
            try:
                st.config(dut, command, skip_error_check=skip_error, type=cli_type)
            except Exception as e:
                st.log(e)
                return False

    command = []
    for _, if_data in vlan_data.items():
        vlan_id = if_data['vlan_id']

        range_cmd = False
        if 'range' in if_data.keys():
            range_ids = if_data['range']
            if range_ids[0] < range_ids[1] :
                range_min, range_max = range_ids[0], range_ids[1]
                range_cmd = True
            elif range_ids[0] > range_ids[1] :
                range_min, range_max = range_ids[1], range_ids[0]
                range_cmd = True
            else :
                vlan_id = range_ids[0]

        if not range_cmd :
            if cli_type == 'click':
                cmd_str = "sudo config vlan {} {} ".format(config, vlan_id)
                command.append(cmd_str)
            elif cli_type == 'klish':
                cmd_str = 'no ' if config =='del' else ''
                cmd_str += "interface Vlan {}".format(vlan_id)
                command.append(cmd_str)
                if config =='add' :
                    command.append('exit')
        elif st.is_feature_supported("vlan-range", dut) and cli_type != 'klish':
            if cli_type == 'click':
                cmd_str = "sudo config vlan range {} {} {}".format(config, range_min, range_max)
                command.append(cmd_str)
        else :
            for vid in range(range_min, range_max+1):
                if cli_type == 'click':
                    cmd_str = "sudo config vlan {} {} ".format(config, vid)
                    command.append(cmd_str)
                elif cli_type == 'klish':
                    cmd_str = 'no ' if config =='del' else ''
                    cmd_str += "interface Vlan {}".format(vid)
                    command.append(cmd_str)
                    if config =='add' :
                        command.append('exit')

    if cli_type in ['click', 'klish'] :
        try:
            st.config(dut, command, type=cli_type)
        except Exception as e:
            st.log(e)
            return False

    command = []
    if config == 'add' :
        for _, if_data in vlan_data.items():
            vlan_id = if_data['vlan_id']

            range_cmd = False
            if 'range' in if_data.keys():
                range_ids = if_data['range']
                if range_ids[0] < range_ids[1] :
                    range_min, range_max = range_ids[0], range_ids[1]
                    range_cmd = True
                elif range_ids[0] > range_ids[1] :
                    range_min, range_max = range_ids[1], range_ids[0]
                    range_cmd = True
                else :
                    vlan_id = range_ids[0]

            for link_member in if_data['members'] :

                if cli_type == 'klish':
                    intf_info = get_interface_number_from_name(link_member)
                    cmd_str = 'interface {} {}'.format(intf_info["type"], intf_info["number"])
                    command.append(cmd_str)

                if not range_cmd :
                    if cli_type == 'click' :
                        cmd_str = "config vlan member {} {} {} ".format(config, vlan_id, link_member)
                        command.append(cmd_str)
                    elif cli_type == 'klish':
                        cmd_str = "switchport trunk allowed Vlan {}".format(vlan_id)
                        command.append(cmd_str)
                elif st.is_feature_supported("vlan-range", dut):
                    if cli_type == 'click' :
                        cmd_str = "config vlan member range {} {} {} {}".format(config, range_min, range_max, link_member)
                        command.append(cmd_str)
                    elif cli_type == 'klish':
                        cmd_str = "switchport trunk allowed Vlan {}-{}".format(range_min, range_max)
                        command.append(cmd_str)
                else:
                    for vid in range(range_min, range_max+1):
                        if cli_type == 'click' :
                            cmd_str = "config vlan member {} {} {} ".format(config, vid, link_member)
                            command.append(cmd_str)
                        elif cli_type == 'klish':
                            cmd_str = "switchport trunk allowed Vlan {}".format(vid)
                            command.append(cmd_str)

                if cli_type == 'klish':
                     command.append('exit')

        if cli_type in ['click', 'klish'] :
            try:
                st.config(dut, command, type=cli_type)
            except Exception as e:
                st.log(e)
                return False

    return True


def config_interface_vrf_binds(dut, if_vrf_data={}, config='yes', cli_type=''):

    if config == 'yes' or config == 'add':
        config = 'bind'
    elif config == 'no' or config == 'del':
        config = 'unbind'
    else :
        st.error("Invalid config type {}".format(config))
        return False

    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    command = []
    for if_name, if_data in if_vrf_data.items():
        vrf = if_data['vrf']
        if cli_type == 'click':
            cmd_str = "sudo config interface vrf {} {} {} ".format(config, if_name, vrf)
            command.append(cmd_str)
        elif cli_type == 'klish':
            intf_info = get_interface_number_from_name(if_name)
            cmd_str = 'interface {} {}'.format(intf_info["type"], intf_info["number"])
            command.append(cmd_str)
            cmd_str = "no " if config == 'unbind' else ''
            cmd_str += "ip vrf forwarding {}".format(vrf)
            command.append(cmd_str)
            command.append('exit')
        elif cli_type in ['rest-patch', 'rest-put']:
            st.log("Spytest API not yet supported for REST type")
            return False
        else:
            st.log("Unsupported CLI TYPE {}".format(cli_type))
            return False

    if cli_type in ['click', 'klish'] :
        try:
            st.config(dut, command, type=cli_type)
        except Exception as e:
            st.log(e)
            return False

    return True


def config_portgroup_property(dut, portgroup, value, property="speed", skip_error=False, cli_type=""):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """
    Function to configure portgroup properties
    Author: Ramprakash Reddy (ramprakash-reddy.kanala@broadcom.com)
    :param dut:
    :param portgroup:
    :param value:
    :param property:
    :param skip_error:
    :param cli_type:
    :return:
    """
    command = "config portgroup {} {} {}".format(property, portgroup, value)
    st.config(dut, command, skip_error_check=skip_error, type=cli_type)
    return True


def show_portgroup(dut, interface=None, cli_type=""):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """
    API to get the list of port groups available in DUT
    Author: Chaitanya Vella (chaitanya.vella-kumar@broadcom.com)
    :param dut:
    :param interface:
    :return: [{'ports': ['Ethernet0', 'Ethernet1', 'Ethernet2', 'Ethernet3', 'Ethernet4',
    'Ethernet5', 'Ethernet6', 'Ethernet7', 'Ethernet8', 'Ethernet9', 'Ethernet10', 'Ethernet11'],
    'valid_speeds': ['25000', '10000', '1000'], 'portgroup': '1'},
    {'ports': ['Ethernet12', 'Ethernet13', 'Ethernet14', 'Ethernet15', 'Ethernet16', 'Ethernet17',
    'Ethernet18', 'Ethernet19', 'Ethernet20', 'Ethernet21', 'Ethernet22', 'Ethernet23'],
    'valid_speeds': ['25000', '10000', '1000'], 'portgroup': '2'}, {'ports': ['Ethernet24',
    'Ethernet25', 'Ethernet26', 'Ethernet27', 'Ethernet28', 'Ethernet29', 'Ethernet30', 'Ethernet31',
    'Ethernet32', 'Ethernet33', 'Ethernet34', 'Ethernet35'], 'valid_speeds': ['25000', '10000', '1000'],
    'portgroup': '3'}, {'ports': ['Ethernet36', 'Ethernet37', 'Ethernet38', 'Ethernet39', 'Ethernet40',
    'Ethernet41', 'Ethernet42', 'Ethernet43', 'Ethernet44', 'Ethernet45', 'Ethernet46', 'Ethernet47'],
    'valid_speeds': ['25000', '10000', '1000'], 'portgroup': '4'}]
    """
    response=list()
    command = "show portgroup"
    output = st.show(dut, command, type=cli_type)
    if output:
        for data in output:
            port_range = data["ports"].replace("Ethernet", "").split("-")
            res = dict()
            res["ports"] = list()
            for i in range(int(port_range[0]), int(port_range[1]) + 1):
                if not interface:
                    res["ports"].append("Ethernet{}".format(i))
                else:
                    if interface == "Ethernet{}".format(i):
                        res["ports"].append("Ethernet{}".format(i))
                        break
            if res["ports"]:
                res["portgroup"] = data["portgroup"]
                res["valid_speeds"] = data["valid_speeds"].split(",")
                response.append(res)
            if interface and res["ports"]:
                break
    return response

def verify_portgroup(dut, **kwargs):
    """
    API to verify portgroup
    Author: Chaitanya Vella (chaitanya.vella-kumar@broadcom.com)
    :param dut:
    :param kwargs: {"cli_type":"click","interface":"Ethernet5","portgroup":"1","speed":"1000"}
    :return:
    """
    cli_type = kwargs.get("cli_type","click")
    interface = kwargs.get("interface", None)
    portgroup = kwargs.get("portgroup", None)
    speed = kwargs.get("speed", None)
    output = show_portgroup(dut, interface=interface,cli_type=cli_type)
    if not output:
        st.log("Empty output observed - {}".format(output))
        return False
    for data in output:
        if portgroup and str(data["portgroup"]) != str(portgroup):
            return False
        if speed and str(speed) not in data["speed"]:
            return False
    return True

def is_port_group_supported(dut, cli_type=""):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    """
    API to check whether port group is supported or not
    Author: Chaitanya Vella (chaitanya.vella-kumar@broadcom.com)
    :param dut:
    :return: False -- Unsupported
             True  -- Supported
    """
    output = show_portgroup(dut, cli_type=cli_type)
    if not output:
        return False
    else:
        return True


def config_ifname_type(dut, config='yes', cli_type=""):

    """
    Function to configure interface naming(Modes: native: Ethernet0, standard: Eth1/1)
    Author: Lakshminarayana D (lakshminarayana.d@broadcom.com)
    :param dut:
    :param config:
    :param cli_type:
    :return:
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    if cli_type in ['click', 'vtysh']:
        st.error("interface-naming command not available in {}".format(cli_type))
        return False
    elif cli_type == 'klish':
        config = '' if config == 'yes' else 'no'
        command = "{} interface-naming standard".format(config)
        st.config(dut, command, type=cli_type)
        st.config(dut, 'pwd', cli_type='click')
        show_ifname_type(dut, cli_type=cli_type)
    else:
        st.error("Provided invalid CLI type-{}".format(cli_type))
        return False
    return True


def show_ifname_type(dut, cli_type=''):
    """
    API to verify interface naming
    Author: Lakshminarayana D (lakshminarayana.d@broadcom.com)
    :param dut:
    :param cli_type:
    :return:
    """
    cli_type = "klish" if cli_type == '' else cli_type
    command = 'show interface-naming'
    if cli_type in ['click', 'vtysh']:
        st.error("show interface-naming command not available in {}".format(cli_type))
        return False
    elif cli_type == 'klish':
        output = st.show(dut, command, type=cli_type)
    else:
        st.error("Provided invalid CLI type-{}".format(cli_type))
        return False

    if not output:
        return None
    return output


def verify_ifname_type(dut, mode='native', cli_type=''):
    """
    API to verify interface naming either native or standard
    Author: Lakshminarayana D (lakshminarayana.d@broadcom.com)
    :param dut:
    :param cli_type:
    :param mode: default is native
    :return:
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)
    output = show_ifname_type(dut, cli_type=cli_type)

    if not output:
        st.error("Empty output observed - {}".format(output))
        return False

    if output[0]['mode'] != mode:
        return False
    return True


def get_ifname_alias(dut, intf_list=None, cli_type=''):
    """
    API to return alternate name(s) for given native interface name(s)
    Author: Lakshminarayana D (lakshminarayana.d@broadcom.com)
    :param dut:
    :param cli_type:
    :param intf_list: [Ethernet0, Ethernet1]
    :return: API will return alternate name for provided interface name. Ethernet0-Eth1/1
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    if cli_type in ['click']:
        alias_list = get_interface_property(dut, intf_list, 'alias', cli_type=cli_type)
    else:
        alias_list = get_interface_property(dut, intf_list, 'altname', cli_type=cli_type)
    if not alias_list:
        st.error("Empty output observed - {}".format(alias_list))
        return False
    return alias_list

def get_physical_ifname_map(dut, cli_type=''):
    """
    API to return interface native to alias mapping
    Author: Lakshminarayana D (lakshminarayana.d@broadcom.com)
    :param dut:
    :param cli_type:
    :return: API will return native to alias map
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    output = interface_status_show(dut, cli_type=cli_type)
    prop = "alias" if cli_type in ['click'] else "altname"
    entries = filter_and_select(output, ["interface", prop])
    retval = OrderedDict()
    for entry in entries:
        interface, alias = entry["interface"], entry[prop]
        if interface.startswith("Ethernet"):
            retval[interface] = alias
        elif interface.startswith("Eth"):
            retval[alias] = interface
    return retval


def get_native_interface_name(dut, if_name, cli_type=''):
    """
    API to return native interface name(s)
    Author: naveen.suvarna@broadcom.com
    :param dut:
    :if_name: Interface name string or list of strings
    :param cli_type:
    :return: API will return native name if its a Ethernet physical
             interface else same input name will be returned
             if input if_name type is list, return type will be list
             else return type will be string
    """

    if isinstance(if_name, list) :
        if_name_list = if_name
    else :
        if_name_list = [ if_name ]

    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    ntv_if_list = []
    show_if_entries = None
    name_field = 'interface'
    alias_field = "alias" if cli_type in ['click'] else "altname"
    phy_if_types = ["Ethernet", "ethernet", "Eth", "eth"]

    for curr_if in if_name_list :
        if curr_if == '' :
            ntv_if_list.append('')
            continue

        phy_interface = False
        for intf_prefix in phy_if_types :
            if curr_if.startswith(intf_prefix) :
                phy_interface = True
                break

        if phy_interface != True :
            ntv_if_list.append(curr_if)
            continue

        intf_info = get_interface_number_from_name(curr_if)
        if not intf_info:
            st.error("Interface data not found for {} ".format(curr_if))
            ntv_if_list.append(curr_if)
            continue

        if intf_info["type"] not in phy_if_types :
            ntv_if_list.append(curr_if)
            continue

        if show_if_entries is None :
            output = interface_status_show(dut, cli_type=cli_type)
            show_if_entries = filter_and_select(output, [name_field, alias_field])

        #found = False
        for if_entry in show_if_entries:
            interface, alias_name = if_entry[name_field], if_entry[alias_field]
            if interface == curr_if or  alias_name == curr_if :
                if interface.startswith("Ethernet"):
                    ntv_if_list.append(interface)
                    #found = True
                    break
                elif alias_name.startswith("Ethernet"):
                    ntv_if_list.append(alias_name)
                    #found = True
                    break

        #if found == False :
            #ntv_if_list.append(one_if)

    if isinstance(if_name, list) :
        st.log("Get Native interface names {} -> {}.".format(if_name, ntv_if_list))
        return ntv_if_list
    else :
        st.log("Get Native interface name {} -> {}.".format(if_name, ntv_if_list[0]))
        return ntv_if_list[0]

