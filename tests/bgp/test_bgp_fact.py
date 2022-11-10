import pytest

from tests.common.utilities import wait_until

pytestmark = [
    pytest.mark.topology('any'),
    pytest.mark.device_type('vs')
]


@pytest.fixture(scope='module', autouse=True)
def tmp_static_arp_workaround(tbinfo, nbrhosts, duthost):
    mg_facts = duthost.get_extended_minigraph_facts(tbinfo)
    config_facts = duthost.get_running_config_facts()
    eos_peers_config = {}
    sonic_peers_config = []

    # Collect info about peers IP, MAC, ifaces
    for iface_info in mg_facts['minigraph_interfaces']:
        sonic_local_ip_addr = iface_info['addr']
        sonic_local_port = config_facts['port_alias_to_name_map'][iface_info['attachto']]
        sonic_local_port_alias = iface_info['attachto']
        sonic_local_port_mac = duthost.get_dut_iface_mac(sonic_local_port)

        eos_peer_ip_addr = iface_info['peer_addr']
        eos_peer_name = mg_facts['minigraph_neighbors'][sonic_local_port_alias]['name']
        eos_peer_port = mg_facts['minigraph_neighbors'][sonic_local_port_alias]['port']

        peer_config_dict = {'port': eos_peer_port, 'ip': sonic_local_ip_addr, 'mac': sonic_local_port_mac}
        eos_peers_config[eos_peer_name] = peer_config_dict

        eos_iface_mac = nbrhosts[eos_peer_name]['host'].get_dut_iface_mac(eos_peer_port)
        sonic_peers_config.append({'port': sonic_local_port, 'ip': eos_peer_ip_addr, 'mac': eos_iface_mac})

    # Configure peers static ARP
    for host_name, nbr in nbrhosts.items():
        config = eos_peers_config[host_name]
        nbr['host'].eos_config(lines=['arp {} {} arpa'.format(config['ip'], config['mac'])])

    # Configure SONiC static ARP
    for item in sonic_peers_config:
        duthost.shell('sudo ip neigh add {} dev {} lladdr {}'.format(item['ip'], item['port'], item['mac']),
                      module_ignore_errors=True)
        duthost.shell('sudo ip neigh change {} dev {} lladdr {}'.format(item['ip'], item['port'], item['mac']),
                      module_ignore_errors=True)

    # Wait untill BGP established
    bgp_neighbors = config_facts.get('BGP_NEIGHBOR', {})
    wait_until(300, 10, 0, duthost.check_bgp_session_state, bgp_neighbors.keys())

    yield

    # Remove peers static ARP
    for item in sonic_peers_config:
        duthost.shell('sudo ip neigh flush dev {}'.format(item['port']), module_ignore_errors=True)

    # Remove SONiC static ARP
    for host_name, nbr in nbrhosts.items():
        config = eos_peers_config[host_name]
        nbr['host'].eos_config(lines=['no arp {}'.format(config['ip'])])


def test_bgp_facts(duthosts, enum_frontend_dut_hostname, enum_asic_index):
    """compare the bgp facts between observed states and target state"""

    duthost = duthosts[enum_frontend_dut_hostname]

    bgp_facts = duthost.bgp_facts(instance_id=enum_asic_index)['ansible_facts']
    namespace = duthost.get_namespace_from_asic_id(enum_asic_index)
    config_facts = duthost.config_facts(host=duthost.hostname, source="running", namespace=namespace)['ansible_facts']

    sonic_db_cmd = "sonic-db-cli {}".format("-n " + namespace if namespace else "")
    for k, v in bgp_facts['bgp_neighbors'].items():
        # Verify bgp sessions are established
        assert v['state'] == 'established'
        # Verify local ASNs in bgp sessions
        assert v['local AS'] == int(config_facts['DEVICE_METADATA']['localhost']['bgp_asn'].encode().decode("utf-8"))
        # Check bgpmon functionality by validate STATE DB contains this neighbor as well
        state_fact = duthost.shell('{} STATE_DB HGET "NEIGH_STATE_TABLE|{}" "state"'
                                   .format(sonic_db_cmd, k), module_ignore_errors=False)['stdout_lines']
        assert state_fact[0] == "Established"

    # In multi-asic, would have 'BGP_INTERNAL_NEIGHBORS' and possibly no 'BGP_NEIGHBOR' (ebgp) neighbors.
    nbrs_in_cfg_facts = {}
    nbrs_in_cfg_facts.update(config_facts.get('BGP_NEIGHBOR', {}))
    nbrs_in_cfg_facts.update(config_facts.get('BGP_INTERNAL_NEIGHBOR', {}))
    # In VoQ Chassis, we would have BGP_VOQ_CHASSIS_NEIGHBOR as well.
    nbrs_in_cfg_facts.update(config_facts.get('BGP_VOQ_CHASSIS_NEIGHBOR', {}))
    for k, v in nbrs_in_cfg_facts.items():
        # Compare the bgp neighbors name with config db bgp neighbors name
        assert v['name'] == bgp_facts['bgp_neighbors'][k]['description']
        # Compare the bgp neighbors ASN with config db
        assert int(v['asn'].encode().decode("utf-8")) == bgp_facts['bgp_neighbors'][k]['remote AS']
