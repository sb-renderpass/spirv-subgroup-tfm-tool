import argparse


g_is_verbose = True


def log(*args):
    if g_is_verbose:
        print(*args)


def try_int(x):
    try:
        return int(x)
    except ValueError:
        return x


class Inst:

    def __init__(self, line):
        tokens = line.split(' = ')
        if len(tokens) == 2:
            self.result_id = tokens[0]
            self.operation = tokens[1]
            self.ops = tokens[1].split()
        else:
            self.result_id = ''
            self.operation = tokens[0]

        tokens = self.operation.split()
        self.opcode   = tokens[0]
        self.operands = tokens[1:]
        #self.operands = [try_int(x) for x in tokens[1:]]

    def __repr__(self):
        operands = ' '.join(self.operands)
        return f'{self.result_id} = {self.opcode} {operands}' \
            if self.result_id != '' \
            else f'{self.opcode} {operands}'

    @staticmethod
    def make_comment(msg):
        return Inst(f'; {msg}')

    @staticmethod
    def make_broadcast(src, dst, tid, data_type):
        return Inst(f'{dst} = OpGroupNonUniformBroadcast {data_type} %uint_3 {src} {tid}')

    @staticmethod
    def make_reduce(src, dst, op, data_type):
        return Inst(f'{dst} = OpGroupNonUniform{op} {data_type} %uint_3 Reduce {src}')

    @staticmethod
    def make_const(name, data_type, value):
        return Inst(f'%{name} = OpConstant %{data_type} {value}')

    @staticmethod
    def make_capability(name):
        return Inst(f'OpCapability {name}')

    def is_ld(self):
        return self.opcode == 'OpLoad'

    def is_st(self):
        return self.opcode == 'OpStore'

    def is_var(self):
        return self.opcode == 'OpVariable'

    def is_ieq(self):
        return self.opcode == 'OpIEqual'

    def is_shared_var(self):
        return self.is_var() and self.get_storage_class() == 'Workgroup'

    def is_atomic(self):
        return self.opcode in ['OpAtomicIAdd']

    def is_br(self):
        return self.opcode == 'OpBranch'

    def is_cbr(self):
        return self.opcode == 'OpBranchConditional'

    def is_ret(self):
        return self.opcode == 'OpReturn'

    def is_ptr(self):
        return self.opcode == 'OpTypePointer'

    def is_const(self):
        return self.opcode == 'OpConstant'

    def is_label(self):
        return self.opcode == 'OpLabel'

    def is_barrier(self):
        return \
            self.opcode == 'OpMemoryBarrier' or \
            self.opcode == 'OpControlBarrier'

    def is_access_chain(self):
        return self.opcode == 'OpAccessChain'

    def get_src(self):
        assert(self.is_st() or self.is_ld() or self.is_cbr() or self.is_ieq() or self.is_atomic())
        if self.is_ieq():
            return self.operands[1:3]
        if self.is_st() or self.is_ld():
            return self.operands[1]
        elif self.is_cbr():
            return self.operands[0]
        elif self.is_atomic():
            return self.operands[4]

    def get_dst(self):
        assert(self.is_st() or self.is_ld() or self.is_cbr() or self.is_br() or self.is_atomic())
        if self.is_cbr():
            return self.operands[1:3]
        elif self.is_atomic():
            return self.operands[1]
        elif self.is_st() or self.is_br():
            return self.operands[0]
        elif self.is_ld():
            return self.result_id

    def get_storage_class(self):
        assert(self.is_var() or self.is_ptr())
        if self.is_var():
            return self.operands[1]
        elif self.is_ptr():
            return self.operands[0]

    def get_base(self):
        assert(self.is_access_chain())
        return self.operands[1]

    # For OpVariable
    def get_ptr_type(self):
        assert(self.is_var())
        return self.operands[0]

    # For OpTypePointer
    def get_type(self):
        assert(self.is_ptr())
        return self.operands[1]

class Module:

    def __init__(self, data):
        self.instructions = [Inst(line.strip()) for line in data]
        self.indents = [' ' * (len(line) - len(line.lstrip())) for line in data]
        self.leaders = calculate_leaders(self.instructions)

    def __repr__(self):
        return '\n'.join([f'{n:3d} | {str(inst)}' for n, inst in enumerate(self.instructions)])

    def get(self, n):
        return self.instructions[n]

    def set(self, n, inst):
        self.instructions[n] = inst
        self._update(inst)

    def move(self, old_loc, inst, new_loc):
        self.instructions.insert(new_loc, inst)
        self.indents.insert(new_loc, self.indents[old_loc])
        self.disable(old_loc) # Internally does an update

    def insert(self, loc, inst):
        self.instructions.insert(loc, inst)
        self.indents.insert(loc, ' ') # TODO: Calculate indent required
        self._update(inst)

    def append(self, opcode, inst):
        # TODO Only insert if not in instruction list
        loc = find_last_inst(self.instructions, opcode)[0]
        self.instructions.insert(loc + 1, inst)
        self.indents.insert(loc + 1, self.indents[loc])
        self._update(inst)

    def disable(self, n):
        # TODO: Append original instruction in comment?
        self.instructions[n] = Inst('; NOP')
        self.indents[n] = ''
        self._update(self.instructions[n])

    def save(self, filename):
        with open(filename, 'w') as out_file:
            for indents, inst in zip(self.indents, self.instructions):
                line = f'{indents}{str(inst)}\n'
                out_file.write(line)

    def _update(self, inst):
        if inst.is_br() or inst.is_cbr() or inst.is_ret() or inst.is_barrier():
            self.leaders = calculate_leaders(self.instructions)

def find_br_dst(instructions, br_dst):
    return next((n, inst) for n, inst in enumerate(instructions) \
         if inst.is_label() and inst.result_id == br_dst)

def find_st(instructions, src):
    return next((n, inst) for n, inst in enumerate(instructions) \
         if inst.is_st() and inst.get_src() == src)

def find_result_id(instructions, result_id):
    return next(((n, inst) for n, inst in enumerate(instructions) \
        if inst.result_id == result_id), None)

def find_leader(module, num):
    i = next(i for i, n in enumerate(module.leaders) if n > num)
    n = module.leaders[i - 1]
    return (n, module.instructions[n])

def find_cbr_with_src(instructions, src):
    return next(((n, inst) for n, inst in enumerate(instructions) \
        if inst.is_cbr() and \
        inst.get_src() == src),
        None)

def find_cbr_with_dst(instructions, dst):
    return next(((n, inst) for n, inst in enumerate(instructions) \
        if inst.is_cbr() and \
        (inst.get_dst()[0] == dst or inst.get_dst()[1] == dst)),
        None)

def find_condition(instructions, result_id):
    inst = find_cbr_with_dst(instructions, result_id)
    return find_result_id(instructions, inst[1].get_src()) if inst else None

def find_last_inst(instructions, opcode):
    return next((n, inst) for n, inst in reversed(list(enumerate(instructions))) \
        if inst.opcode == opcode)

def get_mem_type(instructions, operand):
    inst = find_result_id(instructions, operand)
    inst = find_result_id(instructions, inst[1].get_ptr_type())
    return inst[1].get_type()

def calculate_leaders(instructions):
    leaders = set([0])
    for n, inst in enumerate(instructions):
        if inst.is_br():
            leaders.add(n + 1)
            leaders.add(find_br_dst(instructions, inst.get_dst())[0])
        elif inst.is_cbr():
            leaders.add(n + 1)
            leaders.add(find_br_dst(instructions, inst.get_dst()[0])[0])
            leaders.add(find_br_dst(instructions, inst.get_dst()[1])[0])
        elif inst.is_ret():
            leaders.add(n + 1)
        elif inst.is_barrier():
            leaders.add(n + 1)
    return sorted(leaders)

def is_shared_wr(instructions, inst):
    return inst.is_st() and \
        find_result_id(instructions, inst.get_dst())[1].is_shared_var()

def is_shared_rd(instructions, inst):
    return inst.is_ld() and \
        find_result_id(instructions, inst.get_src())[1].is_shared_var()

def is_shared_atomic_wr(instructions, inst):
    return inst.is_atomic() and \
        find_result_id(instructions, inst.get_dst())[1].is_shared_var()

def is_thread_id(instructions, operand):
    ld_inst = find_result_id(instructions, operand)[1]
    if ld_inst.is_ld():
        tid_inst = find_result_id(instructions, ld_inst.get_src())[1]
        if tid_inst.get_base() == '%gl_LocalInvocationID':
            return True
    return False

def is_in_one_thread_block(module, n):
    inst = find_leader(module, n)[1]
    inst = find_condition(module.instructions, inst.result_id)
    if inst and is_thread_id(module.instructions, inst[1].get_src()[0]):
        tid = inst[1].get_src()[1]
        cbr = find_cbr_with_src(module.instructions, inst[1].result_id)
        return (tid, cbr)
    return None

def is_in_all_thread_block(module, n):
    return not is_in_one_thread_block(module, n)

def find_one_thread_shared_wr(module):
    result = []
    for n, inst in enumerate(module.instructions):
        if is_shared_wr(module.instructions, inst):
            ret = is_in_one_thread_block(module, n)
            if ret:
                result.append((n, inst, *ret))
    return result

def find_one_thread_shared_rd(module):
    result = []
    for n, inst in enumerate(module.instructions):
        if is_shared_rd(module.instructions, inst):
            ret = is_in_one_thread_block(module, n)
            if ret:
                result.append((n, inst, *ret))
    return result

def find_all_thread_shared_rd(module):
    result = []
    for n, inst in enumerate(module.instructions):
        if  is_shared_rd(module.instructions, inst) and \
            is_in_all_thread_block(module, n):
            data_type = get_mem_type(module.instructions, inst.get_src())
            result.append((n, inst, data_type))
    return result

def find_all_thread_atomic_wr(module):
    result = []
    for n, inst in enumerate(module.instructions):
        if  is_shared_atomic_wr(module.instructions, inst) and \
            is_in_all_thread_block(module, n):
            data_type = inst.operands[0] #TODO: Does this work for memory?
            op = inst.opcode[8:]
            result.append((n, inst, data_type, op))
    return result

def apply_broadcast(module, broadcast_insts):
    for (wr_n, wr_inst, tid, _), \
        (rd_n, rd_inst, data_type) in broadcast_insts:

        # Disable write to shared memory
        module.disable(wr_n)

        # Replace read from shared memory with subgroup broadcast
        module.set(rd_n, Inst.make_broadcast(
            wr_inst.get_src(), rd_inst.get_dst(), tid, data_type))

        # Move read from memory location above broadcast
        # if write instruction uses value from memory
        st_src_inst = find_result_id(module.instructions, wr_inst.get_src())
        if st_src_inst[1].is_ld():
            ld_src_inst = find_result_id(module.instructions, st_src_inst[1].get_src())
            module.move(*ld_src_inst, rd_n - 2)
            module.move(*st_src_inst, rd_n - 1)

def apply_reduce(module, reduce_insts):
    for (wr_n, wr_inst, wr_tid, wr_cbr), \
        (op_n, op_inst, data_type, op), \
        (rd_n, rd_inst, rd_tid, rd_cbr) in reduce_insts:

        # Disable write to shared memory
        module.disable(wr_n)

        # Disable atomic operation
        module.disable(op_n)

        # Disable read from shared memory
        module.disable(rd_n)

        # Add subgroup reduce outside thread block
        label_inst = find_br_dst(module.instructions, rd_cbr[1].get_dst()[1])
        loc = label_inst[0] + 1
        module.insert(loc, Inst.make_reduce(
            op_inst.get_src(), rd_inst.get_dst(), op, data_type))

        # Move the associated store instruction outside the thread block
        st_dst_inst = find_st(module.instructions, rd_inst.get_dst())
        module.move(*st_dst_inst, loc + 1)

def main():
    parser = argparse.ArgumentParser('transform')
    parser.add_argument('-i', '--input',   type=str, default='before.comp.spvasm')
    parser.add_argument('-o', '--output',  type=str, default='after.comp.spvasm')
    parser.add_argument('-v', '--verbose', action=argparse.BooleanOptionalAction, default=False)
    args = parser.parse_args()

    global g_is_verbose
    g_is_verbose = args.verbose

    with open(args.input) as in_file:
        data = in_file.readlines()

    module = Module(data)
    log(module)
    log(module.leaders)

    one_thread_shared_wr = find_one_thread_shared_wr(module)
    all_thread_shared_rd = find_all_thread_shared_rd(module)
    all_thread_atomic_wr = find_all_thread_atomic_wr(module)
    one_thread_shared_rd = find_one_thread_shared_rd(module)

    #log(f'one_thread_shared_wr={one_thread_shared_wr}')
    #log(f'all_thread_shared_rd={all_thread_shared_rd}')
    #log(f'all_thread_atomic_wr={all_thread_atomic_wr}')
    #log(f'one_thread_shared_rd={one_thread_shared_rd}')

    ########## Broadcast ##########

    broadcast_insts = []
    for wr_inst in one_thread_shared_wr:
        for rd_inst in all_thread_shared_rd:
            if  wr_inst[1].get_dst() == rd_inst[1].get_src() and \
                wr_inst[0] < rd_inst[0]:
                broadcast_insts.append((wr_inst, rd_inst))

    if broadcast_insts:
        apply_broadcast(module, broadcast_insts)
        module.append('OpConstant',   Inst.make_const('uint_3', 'uint', 3))
        module.append('OpCapability', Inst.make_capability('GroupNonUniform'))
        module.append('OpCapability', Inst.make_capability('GroupNonUniformBallot'))

    ########## Reduce ##########

    reduce_insts = []
    for wr_inst in one_thread_shared_wr:
        for op_inst in all_thread_atomic_wr:
            for rd_inst in one_thread_shared_rd:
                if  wr_inst[1].get_dst() == op_inst[1].get_dst() and \
                    op_inst[1].get_dst() == rd_inst[1].get_src() and \
                    wr_inst[2] == rd_inst[2] and \
                    wr_inst[0] < op_inst[0] and \
                    op_inst[0] < rd_inst[0]:
                    reduce_insts.append((wr_inst, op_inst, rd_inst))

    if reduce_insts:
        apply_reduce(module, reduce_insts)
        module.append('OpConstant',   Inst.make_const('uint_3', 'uint', 3))
        module.append('OpCapability', Inst.make_capability('GroupNonUniform'))
        module.append('OpCapability', Inst.make_capability('GroupNonUniformArithmetic'))

    module.save(args.output)

if __name__ == '__main__':
    main()

