export const CHANNELS = [
  {
    id: 'general',
    name: '전체 교무회의',
    type: 'all',
    badge: '전원',
    desc: '팀원 전원이 함께 검토하고 리더봇이 실행 계획으로 정리합니다.',
    unit: '1학기 전체'
  },
  {
    id: 'eng1',
    name: '영어I',
    type: 'course',
    course_code: 'ENG1',
    desc: '영어I 수업·평가 설계 및 학생 관찰 기록을 팀원들과 협업합니다.',
    unit: '3과'
  },
  {
    id: 'adv_eng1',
    name: '심화영어I',
    type: 'course',
    course_code: 'ADV_ENG1',
    desc: '심화영어I 학술 텍스트 분석 및 심화 논술 평가를 준비합니다.',
    unit: '2과'
  },
  {
    id: 'adv_read1',
    name: '심화영어독해I',
    type: 'course',
    course_code: 'ADV_READ1',
    desc: '심화영어독해I 수능·학평 연계 지문 분석과 문항을 출제합니다.',
    unit: '12강'
  },
  {
    id: 'career_eng',
    name: '진로영어',
    type: 'course',
    course_code: 'CAREER_ENG',
    desc: '진로영어 맞춤형 프로젝트 및 포트폴리오 평가를 관리합니다.',
    unit: '1과'
  }
];

export const BOTS = [
  {
    id: 'coordinator',
    name: '코디봇',
    role: '총괄·디스패치',
    provider: 'Gemini',
    color: 'bg-indigo-600',
    lightColor: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    avatar: '🎯'
  },
  {
    id: 'curriculum',
    name: '교육과정봇',
    role: '성취기준·팩트체크',
    provider: 'Gemini',
    color: 'bg-emerald-600',
    lightColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    avatar: '📐'
  },
  {
    id: 'lesson',
    name: '수업봇',
    role: '차시·활동 설계',
    provider: 'Gemini',
    color: 'bg-blue-600',
    lightColor: 'bg-blue-50 text-blue-700 border-blue-200',
    avatar: '💡'
  },
  {
    id: 'assessment',
    name: '평가봇',
    role: '문항·루브릭',
    provider: 'Gemini',
    color: 'bg-purple-600',
    lightColor: 'bg-purple-50 text-purple-700 border-purple-200',
    avatar: '📝'
  },
  {
    id: 'record',
    name: '기록봇',
    role: '관찰·세특',
    provider: 'Gemini',
    color: 'bg-amber-600',
    lightColor: 'bg-amber-50 text-amber-700 border-amber-200',
    avatar: '📋'
  }
];

export const CONTEXT_NOTES = {
  eng1: {
    course: '영어I',
    unit: '3과 (Lesson 3. Healthy Living, Healthy Life)',
    progress: '총 12차시 중 7차시 진행 중 (58%)',
    standards: [
      '[12영I03-02] 일상생활이나 친숙한 일반적 주제에 관한 글을 읽고 세부 정보를 파악할 수 있다.',
      '[12영I04-03] 친숙한 일반적 주제에 관해 자신의 의견이나 감정을 간단한 문장으로 쓸 수 있다.'
    ],
    notes: '3과 본문 독해 완료 후 서술형 수행평가(논술형 1문항) 연계 차시 준비 중'
  },
  general: {
    course: '전체 공통 (2026학년도 1학기)',
    unit: '정규 학사 및 평가 계획',
    progress: '1학기 교과 협의회 진행 중',
    standards: [
      '2022 개정 교육과정 고등학교 영어과 공통 성취기준 준수',
      '학교생활기록부 기재요령 및 학업성적관리규정 엄수'
    ],
    notes: '전체 4개 개설 과목의 진도율 및 수행평가 반영 비율 조율'
  },
  adv_eng1: {
    course: '심화영어I',
    unit: '2과 (Unit 2. Environmental Economics)',
    progress: '총 16차시 중 4차시 진행 중 (25%)',
    standards: [
      '[12심영I03-04] 학술적 주제의 글에서 논증 구조와 저자의 주장을 비판적으로 평가할 수 있다.'
    ],
    notes: '학술 에세이 작성 및 피어 리뷰 프로젝트 단계별 비계 제공'
  },
  adv_read1: {
    course: '심화영어독해I',
    unit: '수능 연계 12강 (인문·철학 지문)',
    progress: '총 14차시 중 9차시 진행 중 (64%)',
    standards: [
      '[12심독I03-01] 인문·사회·자연과학 분야의 복합적 글을 읽고 핵심 함의를 추론할 수 있다.'
    ],
    notes: '수능 빈출 고난도 지문 심층 분석 및 어휘 티어링 집중 지도'
  },
  career_eng: {
    course: '진로영어',
    unit: '1과 (Unit 1. Global Careers & Aspirations)',
    progress: '총 10차시 중 3차시 진행 중 (30%)',
    standards: [
      '[12진영04-02] 진로 및 직업 관련 정보를 탐색하고 이를 영문으로 요약·발표할 수 있다.'
    ],
    notes: '학생별 희망 진로 연계 맞춤형 영문 이력서 포트폴리오 구상'
  }
};

export const ROUTINES = [
  {
    id: 'r1',
    name: '주간 수능 문항 세트',
    schedule: '매주 월요일 08:30',
    bot: '평가봇',
    status: '활성'
  },
  {
    id: 'r2',
    name: '학기말 세특 배치',
    schedule: '기말고사 후 매일 17:00',
    bot: '기록봇',
    status: '대기'
  }
];

export const MOCK_DELIVERABLE_ENG1 = {
  title: '[영어I 3과] 논술형 문항 및 4수준 루브릭',
  course: '영어I',
  unit: '3과',
  bot: '평가봇',
  reviewer: '교육과정봇',
  createdAt: '2026-11-05 10:14',
  standards: [
    '[12영I03-02] 일상생활이나 친숙한 일반적 주제에 관한 글을 읽고 세부 정보를 파악할 수 있다.',
    '[12영I04-03] 친숙한 일반적 주제에 관해 자신의 의견이나 감정을 간단한 문장으로 쓸 수 있다.'
  ],
  content: `### [문항 1] 논술형 평가 문항 (배점: 10점)

**[지문]**
Regular physical activity and balanced nutritional habits are essential for maintaining cardiovascular health and mental vitality. Recent studies demonstrate that students engaging in at least 30 minutes of aerobic exercise daily report higher cognitive clarity and lower academic stress levels.

**[문항 조건]**
1. 위 지문에서 규칙적인 신체 활동이 주는 긍정적 효과 2가지를 찾아 우리말로 명시하시오.
2. 자신의 일상 습관 중 건강 증진을 위해 개선하고 싶은 점 1가지를 3문장 이상의 완전한 영어 문장으로 논술하시오. (조건: 접속사 1개 이상, 관계대명사 1개 이상 포함)

---

### [4수준 채점 루브릭]

| 수준 | 배점 | 세부 평가 기준 |
| :--- | :--- | :--- |
| **탁월 (A)** | 10~9점 | 신체 활동 효과 2가지를 정확히 제시하고, 일상 개선점을 문법적 오류 없이 조건(3문장 이상, 접속사/관계대명사 활용)을 완벽히 충족하여 유창하게 서술함. |
| **우수 (B)** | 8~7점 | 효과 2가지를 충실히 기술하였으나, 영작에서 경미한 어휘·철자 오류가 1~2회 관찰되거나 문장 간 연결이 다소 부자연스러움. |
| **보통 (C)** | 6~5점 | 효과를 1가지만 서술하였거나, 영작에서 필수 문법 조건 중 일부를 누락하고 의미 전달에 일부 지장이 있는 오류가 발견됨. |
| **미흡 (D)** | 4~0점 | 지문 내용 파악이 미흡하여 효과를 제시하지 못했거나, 영작 문장이 2문장 이하이며 문법적 결함으로 인해 주장을 파악하기 어려움. |`
};

export const INITIAL_MESSAGES = {
  eng1: [
    {
      id: 'm1',
      type: 'user',
      sender: '교사',
      time: '오전 10:14',
      content: '영어I 3과 수행평가 설계해줘. 성취기준 매핑하고 논술형 문항 1개와 4수준 루브릭 작성해줘.'
    },
    {
      id: 'm2',
      type: 'bot_text',
      botId: 'coordinator',
      sender: '코디봇',
      time: '오전 10:14',
      content: '영어I 3과 수행평가 요청을 접수했습니다. 성취기준 분석 및 평가 문항 설계를 위해 교육과정봇과 평가봇에 과업을 분해 배정합니다.'
    },
    {
      id: 'm3',
      type: 'dispatch',
      botId: 'coordinator',
      sender: '코디봇',
      time: '오전 10:14',
      title: '디스패치',
      tasks: [
        {
          id: 'task-1',
          bot: 'curriculum',
          botName: '교육과정봇',
          title: '성취기준 매핑',
          deliverable: '성취기준 2개와 평가 요소'
        },
        {
          id: 'task-2',
          bot: 'assessment',
          botName: '평가봇',
          title: '논술형 문항과 루브릭',
          deliverable: '문항 1개, 4수준 루브릭'
        }
      ]
    },
    {
      id: 'm4',
      type: 'report',
      botId: 'coordinator',
      sender: '코디봇',
      time: '오전 10:15',
      title: '작업 보고',
      reports: [
        { botName: '교육과정봇', text: '전문 영역 검토 완료', count: 1 },
        { botName: '평가봇', text: '전문 영역 검토 완료', count: 1 }
      ],
      note: '팀원들의 의견이 취합되었습니다. 추가 조치가 필요하시면 언제든 말씀해 주세요.'
    },
    {
      id: 'm5',
      type: 'approval',
      botId: 'coordinator',
      sender: '코디봇',
      time: '오전 10:15',
      question: '논술형 1문항과 4수준 루브릭으로 확정하시겠습니까?',
      status: 'pending' // 'pending' | 'approved' | 'rejected'
    }
  ],
  general: [
    {
      id: 'gm1',
      type: 'user',
      sender: '교사',
      time: '오전 09:30',
      content: '이번 학기 영어과 전체 평가 계획 일정 확인 부탁해.'
    },
    {
      id: 'gm2',
      type: 'bot_text',
      botId: 'coordinator',
      sender: '코디봇',
      time: '오전 09:31',
      content: '2026학년도 1학기 지필평가 1회, 수행평가 2회(서술형 논술, 말하기 프로젝트) 일정 초안을 정리했습니다. 과목별 세부 차시안은 각 과목 채널에서 확인하실 수 있습니다.'
    }
  ],
  adv_eng1: [
    {
      id: 'am1',
      type: 'user',
      sender: '교사',
      time: '오전 11:00',
      content: '심화영어I 2단원 학술 에세이 비계(Sentence Frames) 생성해줘.'
    },
    {
      id: 'am2',
      type: 'bot_text',
      botId: 'lesson',
      sender: '수업봇',
      time: '오전 11:01',
      content: '심화영어I 2단원 환경경제학 지문을 바탕으로, 서론 논지 제시 및 반론 반박에 활용할 학술 문장 틀 5종을 설계하였습니다.'
    }
  ],
  adv_read1: [
    {
      id: 'rm1',
      type: 'user',
      sender: '교사',
      time: '오후 01:20',
      content: '수능특강 12강 3번 지문 변형문제(빈칸추론) 1문항 출제해줘.'
    },
    {
      id: 'rm2',
      type: 'bot_text',
      botId: 'assessment',
      sender: '평가봇',
      time: '오후 01:21',
      content: '핵심 개념의 대립쌍 구조를 보존한 고난도 빈칸추론 1문항과 매력적 오답 매트릭스를 구성했습니다.'
    }
  ],
  career_eng: [
    {
      id: 'cm1',
      type: 'user',
      sender: '교사',
      time: '오후 02:45',
      content: '진로 맞춤형 영문 이력서 및 직무 인터뷰 활동지 초안 부탁해.'
    },
    {
      id: 'cm2',
      type: 'bot_text',
      botId: 'lesson',
      sender: '수업봇',
      time: '오후 02:46',
      content: '학생별 희망 진로(IT, 보건의료, 국제통상)를 반영한 영문 Resume 작성 활동지 3차시 패키지를 준비했습니다.'
    }
  ]
};
