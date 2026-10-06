set nocompatible
set encoding=utf-8
set nomore
let s:root = fnamemodify(expand('<sfile>:p'), ':h:h')
execute 'set runtimepath^=' . fnameescape(s:root)
let g:idraaak_anchors_python = [$IDRAAAK_TEST_PYTHON]
runtime plugin/idraaak_anchors.vim
let s:checks = []

function! s:check(label, expected, actual) abort
  call assert_equal(a:expected, a:actual, a:label)
  call add(s:checks, a:label)
endfunction

function! s:wait(buf) abort
  let l:start = reltime()
  while getbufvar(a:buf, 'idraaak_anchors_pending', 0) && reltimefloat(reltime(l:start)) < 5
    sleep 10m
  endwhile
  call assert_equal(0, getbufvar(a:buf, 'idraaak_anchors_pending', 0), 'worker finishes')
endfunction

function! s:article(lines) abort
  enew!
  call setline(1, a:lines)
  setlocal nomodified
  return bufnr('%')
endfunction

try
  call setqflist([], ' ', {'items': [{'text': 'Other tool result'}], 'title': 'Other tool', 'context': {'owner': 'other-tool'}})
  let s:other_id = getqflist({'id': 0}).id
  let s:buf = s:article(['نص 😀 <a href="#مفقود">go</a>', '<h2 id="x">a</h2><h3 id="x">b</h3>', '<a href="#x">go</a>'])
  let s:before = getline(1, '$')
  let s:tick = b:changedtick
  setlocal nomodifiable
  IdraaakAnchorsCheck
  call s:wait(s:buf)
  let s:qf = getqflist()
  call s:check('four real diagnostics in quickfix', 4, len(s:qf))
  call s:check('Arabic and emoji use byte columns', match(s:before[0], '#') + 1, s:qf[0].col)
  call s:check('source text remains unchanged', s:before, getline(1, '$'))
  call s:check('read-only buffer changedtick remains unchanged', s:tick, b:changedtick)
  cfirst
  call s:check('quickfix jumps to the exact attribute', [1, match(s:before[0], '#') + 1], [line('.'), col('.')])
  call s:check('previous quickfix list is preserved', 'Other tool result', getqflist({'id': s:other_id, 'items': 1}).items[0].text)
  setlocal modifiable
  call setline(1, '<h2 id="مفقود">ok</h2>')
  doautocmd TextChanged
  call s:check('editing clears stale diagnostics', [], getqflist())
  call s:check('editing clears saved report', {}, b:idraaak_anchors_report)

  let s:buf = s:article(['<a href="#%D9%82%D8%B3%D9%85">go</a><h2 id="قسم">ok</h2>'])
  IdraaakAnchorsCheck
  call s:wait(s:buf)
  call s:check('valid encoded Arabic article has no issues', [], getqflist())
  call s:check('valid article was actually checked', 1, b:idraaak_anchors_report.links_checked)

  let s:buf = s:article(['<a href="#gone">go</a>'])
  IdraaakAnchorsCheck
  call setline(1, '<h2 id="gone">ok</h2>')
  call s:wait(s:buf)
  call s:check('results from edited snapshot are discarded', {}, get(b:, 'idraaak_anchors_report', {}))

  IdraaakAnchorsCheck
  IdraaakAnchorsClear
  sleep 150m
  call s:check('clear cancels pending work', 0, b:idraaak_anchors_pending)
  call s:check('cancelled work cannot restore diagnostics', {}, b:idraaak_anchors_report)

  let s:buf = s:article(['<a href="#gone">go</a>'])
  IdraaakAnchorsCheck
  call s:wait(s:buf)
  call setqflist([], ' ', {'items': [{'text': 'New other result'}], 'title': 'Other tool again', 'context': {'owner': 'other-tool'}})
  IdraaakAnchorsClear
  call s:check('clear leaves another tool current list intact', 'New other result', getqflist()[0].text)

  let g:idraaak_anchors_python = ['this-python-command-does-not-exist-idraaak']
  IdraaakAnchorsCheck
  call s:check('missing Python does not claim success', 0, get(b:, 'idraaak_anchors_pending', 0))
  call s:check('missing Python preserves unrelated results', 'New other result', getqflist()[0].text)
catch
  call add(v:errors, v:exception . ' @ ' . v:throwpoint)
endtry

let s:result = {'vim_version': execute('version'), 'checks': s:checks, 'errors': v:errors, 'success': empty(v:errors)}
call writefile([json_encode(s:result)], s:root . '/tests/vim-results.json')
if !empty(v:errors)
  cquit
endif
qa!
