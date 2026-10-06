" Idraaak Article Anchors: manual checks for static HTML article fragments.
if exists('g:loaded_idraaak_anchors')
  finish
endif
let g:loaded_idraaak_anchors = 1
command! IdraaakAnchorsCheck call idraaak_anchors#check()
command! IdraaakAnchorsClear call idraaak_anchors#clear(bufnr('%'))
augroup idraaak_article_anchors
  autocmd!
  autocmd TextChanged,TextChangedI,BufWipeout * call idraaak_anchors#invalidate(str2nr(expand('<abuf>')))
augroup END
