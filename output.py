import re
from nodes import NodeVisitor


# Parse tree Node visitor that outputs the original source code. You can
# implement custom transformations by subclassing this class.
class OutputVisitor(NodeVisitor):
    result = [] # Array<Str>
    line_number = 1
    
    omit_next_space = False # If True, omit the next character if
    # it is a space
    indent = 0      # Number of spaces of indent right now
    extra_indent = 0 # Number of spaces of extra indent to add when 
    # encountering a line break
    
    # Return a string representation of the output.
    def output(self):
        return ''.join(self.result)
    
    def visit_mypy_file(self, o):
        self.nodes(o.defs)
        self.token(o.repr.eof)
    
    def visit_import(self, o):
        r = o.repr
        self.token(r.import_tok)
        for i in range(len(r.components)):
            self.tokens(r.components[i])
            if r.as_names[i] is not None:
                self.tokens(r.as_names[i])
            if i < len(r.commas):
                self.token(r.commas[i])
        self.token(r.br)
    
    def visit_import_from(self, o):
        self.output_import_from_or_all(o)
    
    def visit_import_all(self, o):
        self.output_import_from_or_all(o)
    
    def output_import_from_or_all(self, o):
        r = o.repr
        self.token(r.from_tok)
        self.tokens(r.components)
        self.token(r.import_tok)
        self.token(r.lparen)
        for misc, comma in r.names:
            self.tokens(misc)
            self.token(comma)
        self.token(r.rparen)
        self.token(r.br)
    
    def visit_type_def(self, o):
        r = o.repr
        self.tokens([r.class_tok, r.name])
        self.type_vars(o.type_vars)
        self.token(r.lparen)
        for i in range(len(o.base_types)):
            if o.base_types[i].repr is not None:
                self.typ(o.base_types[i])
            if i < len(r.commas):
                self.token(r.commas[i])
        self.token(r.rparen)
        self.node(o.defs)
    
    def type_vars(self, v):
        # IDEA: Combine this with typeVars in outputtype.alo.
        if v is not None and v.repr is not None:
            r = v.repr
            self.token(r.langle)
            for i in range(len(v.items)):
                d = v.items[i]
                self.token(d.repr.name)
                self.token(d.repr.is_tok)
                if d.bound is not None:
                    self.typ(d.bound)
                if i < len(r.commas):
                    self.token(r.commas[i])
            self.token(r.rangle)
    
    def visit_func_def(self, o):
        r = o.repr
        
        if r.def_tok is not None:
            self.token(r.def_tok)
        else:
            self.typ(o.typ.typ.items()[0].ret_type)
        
        self.token(r.name)
        
        self.function_header(o, r.args)
        
        self.node(o.body)
    
    def visit_overloaded_func_def(self, o):
        for f in o.items:
            f.accept(self)
    
    def function_header(self, o, arg_repr, pre_args_func=None, erase_type=False, strip_space_before_first_arg=erase_type):
        r = o.repr
        
        t = None
        if o.typ is not None and not erase_type:
            t = o.typ.typ
        
        init = o.init
        
        if t is not None:
            self.type_vars(t.variables)
        
        self.token(arg_repr.lseparator)
        if pre_args_func is not None:
            pre_args_func()
        for i in range(len(arg_repr.arg_names)):
            if t is not None:
                if t.arg_types[i].repr is not None:
                    self.typ(t.arg_types[i])
            if i == len(arg_repr.arg_names) - 1:
                self.token(arg_repr.asterisk)
            if not erase_type:
                self.token(arg_repr.arg_names[i])
            else:
                n = arg_repr.arg_names[i].rep
                if i == 0 and strip_space_before_first_arg:
                    # Remove spaces before the first argument name. Generally spaces
                    # are only present after a type, and if we erase the type, we should
                    # also erase also the spaces.
                    n = re.sub(n, ' +([a-zA-Z0-9_])$', '\\1')
                self.string(n)
            if i < len(arg_repr.assigns):
                self.token(arg_repr.assigns[i])
            if init is not None and i < len(init) and init[i] is not None:
                self.node(init[i].rvalue)
            if i < len(arg_repr.commas):
                self.token(arg_repr.commas[i])
        self.token(arg_repr.rseparator)
    
    def visit_var_def(self, o):
        r = o.repr
        for v, t in o.items:
            self.typ(t)
            self.node(v)
        self.token(r.assign)
        self.node(o.init)
        self.token(r.br)
    
    def visit_var(self, o):
        r = o.repr
        self.token(r.name)
        self.token(r.comma)
    
    def visit_decorator(self, o):
        self.token(o.repr.at)
        self.node(o.decorator)
        self.token(o.repr.br)
        self.node(o.func)
    
    # Statements
    
    def visit_block(self, o):
        r = o.repr
        self.tokens([r.colon, r.br, r.indent])
        old_indent = self.indent
        self.indent = len(r.indent.string)
        self.nodes(o.body)
        self.token(r.dedent)
        self.indent = old_indent
    
    def visit_global_decl(self, o):
        r = o.repr
        self.token(r.global_tok)
        for i in range(len(r.names)):
            self.token(r.names[i])
            if i < len(r.commas):
                self.token(r.commas[i])
        self.token(r.br)
    
    def visit_expression_stmt(self, o):
        self.node(o.expr)
        self.token(o.repr.br)
    
    def visit_assignment_stmt(self, o):
        r = o.repr
        i = 0
        for lv in o.lvalues:
            self.node(lv)
            self.token(r.assigns[i])
            i += 1
        self.node(o.rvalue)
        self.token(r.br)
    
    def visit_operator_assignment_stmt(self, o):
        r = o.repr
        self.node(o.lvalue)
        self.token(r.assign)
        self.node(o.rvalue)
        self.token(r.br)
    
    def visit_return_stmt(self, o):
        self.simple_stmt(o, o.expr)
    
    def visit_assert_stmt(self, o):
        self.simple_stmt(o, o.expr)
    
    def visit_yield_stmt(self, o):
        self.simple_stmt(o, o.expr)
    
    def visit_del_stmt(self, o):
        self.simple_stmt(o, o.expr)
    
    def visit_break_stmt(self, o):
        self.simple_stmt(o)
    
    def visit_continue_stmt(self, o):
        self.simple_stmt(o)
    
    def visit_pass_stmt(self, o):
        self.simple_stmt(o)
    
    def simple_stmt(self, o, expr=None):
        self.token(o.repr.keyword)
        self.node(expr)
        self.token(o.repr.br)
    
    def visit_raise_stmt(self, o):
        self.token(o.repr.raise_tok)
        self.node(o.expr)
        if o.from_expr is not None:
            self.token(o.repr.from_tok)
            self.node(o.from_expr)
        self.token(o.repr.br)
    
    def visit_while_stmt(self, o):
        self.token(o.repr.while_tok)
        self.node(o.expr)
        self.node(o.body)
        if o.else_body is not None:
            self.token(o.repr.else_tok)
            self.node(o.else_body)
    
    def visit_for_stmt(self, o):
        r = o.repr
        self.token(r.for_tok)
        for i in range(len(o.index)):
            self.node(o.types[i])
            self.token(o.index[i].repr.name)
            self.token(o.index[i].repr.comma)
        self.token(r.in_tok)
        self.node(o.expr)
        
        self.node(o.body)
        if o.else_body is not None:
            self.token(r.else_tok)
            self.node(o.else_body)
    
    def visit_if_stmt(self, o):
        r = o.repr
        self.token(r.if_tok)
        self.node(o.expr[0])
        self.node(o.body[0])
        for i in range(1, len(o.expr)):
            self.token(r.elif_toks[i - 1])
            self.node(o.expr[i])
            self.node(o.body[i])
        self.token(r.else_tok)
        if o.else_body is not None:
            self.node(o.else_body)
    
    def visit_try_stmt(self, o):
        r = o.repr
        self.token(r.try_tok)
        self.node(o.body)
        for i in range(len(o.types)):
            self.token(r.except_toks[i])
            self.node(o.types[i])
            self.token(r.as_toks[i])
            self.node(o.vars[i])
            self.node(o.handlers[i])
        if o.else_body is not None:
            self.token(r.else_tok)
            self.node(o.else_body)
        if o.finally_body is not None:
            self.token(r.finally_tok)
            self.node(o.finally_body)
    
    def visit_with_stmt(self, o):
        self.token(o.repr.with_tok)
        for i in range(len(o.expr)):
            self.node(o.expr[i])
            self.token(o.repr.as_toks[i])
            self.node(o.name[i])
            if i < len(o.repr.commas):
                self.token(o.repr.commas[i])
        self.node(o.body)
    
    # Expressions
    
    def visit_int_expr(self, o):
        self.token(o.repr.int)
    
    def visit_str_expr(self, o):
        self.tokens(o.repr.string)
    
    def visit_float_expr(self, o):
        self.token(o.repr.float)
    
    def visit_paren_expr(self, o):
        self.token(o.repr.lparen)
        self.node(o.expr)
        self.token(o.repr.rparen)
    
    def visit_name_expr(self, o):
        # Supertype references may not have a representation.
        if o.repr is not None:
            self.token(o.repr.id)
    
    def visit_member_expr(self, o):
        self.node(o.expr)
        self.token(o.repr.dot)
        self.token(o.repr.name)
    
    def visit_index_expr(self, o):
        self.node(o.base)
        self.token(o.repr.lbracket)
        self.node(o.index)
        self.token(o.repr.rbracket)
    
    def visit_slice_expr(self, o):
        self.node(o.begin_index)
        self.token(o.repr.colon)
        self.node(o.end_index)
        self.token(o.repr.colon2)
        self.node(o.stride)    
    
    def visit_call_expr(self, o):
        r = o.repr
        self.node(o.callee)
        self.token(r.lparen)
        nargs = len(o.args)
        for i in range(nargs):
            if i == nargs - 1:
                self.token(r.asterisk)
            self.node(o.args[i])
            if i < len(r.commas):
                self.token(r.commas[i])
        i = nargs
        for n, v in o.keyword_args:
            self.node(n)
            self.token(r.assigns[i - nargs])
            self.node(v)
            if i < len(r.commas):
                self.token(r.commas[i])
            i += 1
        self.token(r.rparen)
    
    def visit_op_expr(self, o):
        self.node(o.left)
        self.tokens([o.repr.op, o.repr.op2])
        self.node(o.right)
    
    def visit_cast_expr(self, o):
        self.token(o.repr.lparen)
        self.typ(o.typ)
        self.token(o.repr.rparen)
        self.node(o.expr)
    
    def visit_super_expr(self, o):
        r = o.repr
        self.tokens([r.super_tok, r.lparen, r.rparen, r.dot, r.name])
    
    def visit_unary_expr(self, o):
        self.token(o.repr.op)
        self.node(o.expr)
    
    def visit_list_expr(self, o):
        r = o.repr
        if o.typ is not None:
            self.token(r.langle)
            self.typ(o.typ)
            self.token(r.rangle)
        self.token(r.lbracket)
        self.comma_list(o.items, r.commas)
        self.token(r.rbracket)
    
    def visit_tuple_expr(self, o):
        r = o.repr
        self.token(r.lparen)
        self.comma_list(o.items, r.commas)
        self.token(r.rparen)
    
    def visit_dict_expr(self, o):
        r = o.repr
        if o.key_type is not None:
            self.token(r.langle)
            self.typ(o.key_type)
            self.token(r.type_comma)
            self.typ(o.value_type)
            self.token(r.rangle)
        self.token(r.lbrace)
        i = 0
        for k, v in o.items:
            self.node(k)
            self.token(r.colons[i])
            self.node(v)
            if i < len(r.commas):
                self.token(r.commas[i])
            i += 1
        self.token(r.rbrace)
    
    def visit_func_expr(self, o):
        r = o.repr
        self.token(r.lambda_tok)
        self.function_header(o, r.args)
        self.token(r.colon)
        self.node(o.body.body[0].expr)
    
    def visit_type_application(self, o):
        self.node(o.expr)
        self.token(o.repr.langle)
        self.type_list(o.types, o.repr.commas)
        self.token(o.repr.rangle)
    
    # Types
    
    def visit_annotation(self, o):
        self.typ(o.typ)
    
    # Helpers
    
    def line(self):
        return self.line_number
    
    # Output a string.
    def string(self, s):
        if self.omit_next_space:
            if s.startswith(' '):
                s = s[1:]
            self.omit_next_space = False
        self.line_number += s.count('\n')
        if s != '':
            s = s.replace('\n', '\n' + ' ' * self.extra_indent)
            self.result.append(s)
    
    # Output a token.
    def token(self, t):
        self.string(t.rep)
    
    # Output an array of tokens.
    def tokens(self, a):
        for t in a:
            self.token(t)
    
    # Output a node.
    def node(self, n):
        if n is not None:
            n.accept(self)
    
    # Output an array of nodes.
    def nodes(self, a):
        for n in a:
            self.node(n)
    
    def comma_list(self, items, commas):
        for i in range(len(items)):
            self.node(items[i])
            if i < len(commas):
                self.token(commas[i])
    
    def type_list(self, items, commas):
        for i in range(len(items)):
            self.typ(items[i])
            if i < len(commas):
                self.token(commas[i])
    
    # Output a type.
    def typ(self, t):
        if t is not None:
            v = TypeOutputVisitor()
            t.accept(v)
            self.string(v.output())
    
    def last_output_char(self):
        if self.result != [] and self.result[-1] != '':
            return self.result[-1][-1]
        else:
            return ''