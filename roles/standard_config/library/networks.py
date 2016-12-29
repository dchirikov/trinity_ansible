#!/usr/bin/python

from ansible.module_utils.basic import *
import socket
import struct

def main():
    fields = {
		'interfaces': {"required": True, "type": "list"},
		'facts': {"required": True, "type": "dict"}
                
	}
    module = AnsibleModule(argument_spec=fields)
    response = {
        'trix_if_provision_ip': None,
        'trix_if_provision_net': None,
        'trix_if_provision_prefix': None,
        'trix_if_provision_mask': None,
        'trix_if_provision_domain': None,

        'trix_if_bmc_ip': None,
        'trix_if_bmc_net': None,
        'trix_if_bmc_prefix': None,
        'trix_if_bmc_mask': None,
        'trix_if_bmc_domain': None,

        'trix_if_external_ip': None,
        'trix_if_external_net': None,
        'trix_if_external_prefix': None,
        'trix_if_external_mask': None,
        'trix_if_external_domain': None,

        'trix_if_internal': [],
    }

    facts = module.params['facts']
    interfaces = module.params['interfaces']

    interface_dict = {}
    for interface in interfaces:
        if_data = {
                'ip': None,
                'net': None,
                'mask': None,
                'prefix': None,
                'id': None,
                'domain': None,
            }
        try:
            if_name = interface['DEVICE']
        except KeyError:
            # can do nothing with such interface
            continue

        try:
            if_data['id'] = interface['_IDENTIFIER']
        except KeyError:
            # best we can do is to guess than
            # this interface is internal for the cluster
            if_data['id'] = 'internal'

        try:
            if_data['domain'] = interface['_DOMAIN']
        except KeyError:
            if_data['domain'] = None

        try:
            if_data['prefix'] = int(interface['PREFIX'])
        except KeyError, ValueError:
            if_data['prefix'] = None

        try:
            if_data['mask'] = interface['NETMASK']
        except KeyError:
            if_data['mask'] = None

        try:
            if_data['ip'] = interface['IPADDR']
        except KeyError:
            # if interface has BOOTPROTO=dhcp, for instance
            key_name = "ansible_" + if_name
            try:
                if_data['ip'] = facts[key_name]['ipv4']['address']
                if_data['mask'] = facts[key_name]['ipv4']['netmask']
            except KeyError:
                continue
	# calculate prefix and mask if needed
        if if_data['prefix']:
            prefix_num = ((1<<32) -1) ^ ((1<<(33-if_data['prefix'])-1) -1)
            if_data['mask'] = socket.inet_ntoa(struct.pack('>L', (prefix_num)))
        elif if_data['mask']:
            prefix_num = struct.unpack('>L', (socket.inet_aton(if_data['mask'])))[0]
            bin_mask = bin(prefix_num)[2:]  # dirty and ugly
            if_data['prefix'] = len(bin_mask.rstrip('0'))
        else:
            continue

        net_num = struct.unpack('>L', (socket.inet_aton(if_data['ip'])))[0]
        mask_num = ((1<<32) -1) ^ ((1<<(33-if_data['prefix'])-1) -1)
	if_data['net'] = socket.inet_ntoa(struct.pack('>L', long(net_num & mask_num)))
	interface_dict[if_name] = if_data
        trix_if_internal = []

    # Generate answer

    for interface in interface_dict:
        if_id = interface_dict[interface]['id']
        if_ip = interface_dict[interface]['ip']
        if_net = interface_dict[interface]['net']
        if_mask = interface_dict[interface]['mask']
        if_prefix = interface_dict[interface]['prefix']
        if_domain = interface_dict[interface]['domain'] or interface_dict[interface]['id']
        if if_id == "external":
            response['trix_if_external_ip'] = if_ip
            response['trix_if_external_net'] = if_net
            response['trix_if_external_mask'] = if_mask
            response['trix_if_external_prefix'] = if_prefix
            response['trix_if_external_domain'] = if_domain
            continue
        if if_id == "provisioning":
            response['trix_if_provision_ip'] = if_ip
            response['trix_if_provision_net'] = if_net
            response['trix_if_provision_mask'] = if_mask
            response['trix_if_provision_prefix'] = if_prefix
            response['trix_if_provision_domain'] = if_domain
        if if_id == "bmc":
            response['trix_if_bmc_ip'] = if_ip
            response['trix_if_bmc_net'] = if_net
            response['trix_if_bmc_mask'] = if_mask
            response['trix_if_bmc_prefix'] = if_prefix
            response['trix_if_bmc_domain'] = if_domain
        trix_if_internal.append({
                'ip': if_ip,
                'net': if_net,
                'mask': if_mask,
                'prefix': if_prefix,
                'domain': if_domain,
             })
    response['trix_if_internal'] = trix_if_internal

    module.exit_json(changed=False, meta=response)


if __name__ == '__main__':  
    main()
