// 招聘平台搜索入口
export const PLATFORMS = [
  { id: 'boss', name: 'BOSS直聘', url: (k) => `https://www.zhipin.com/web/geek/job?query=${k}` },
  { id: 'zhaopin', name: '智联招聘', url: (k) => `https://sou.zhaopin.com/?kw=${k}` },
  { id: 'liepin', name: '猎聘', url: (k) => `https://www.liepin.com/zhaopin/?key=${k}` },
  { id: '51job', name: '前程无忧', url: (k) => `https://search.51job.com/list/000000,000000,0000,00,9,99,${k},2,1.html` },
  { id: 'lagou', name: '拉勾', url: (k) => `https://www.lagou.com/wn/jobs?kd=${k}` },
]

export const platformUrl = (p, keyword) => p.url(encodeURIComponent(keyword || ''))
