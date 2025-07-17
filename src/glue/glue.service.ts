// glue.service.ts
import { Injectable } from '@nestjs/common';
import { Glue } from 'aws-sdk';

@Injectable()
export class GlueService {
  private glue = new Glue({ region: process.env.AWS_REGION });

  async startJob(jobName: string): Promise<void> {
    await this.glue.startJobRun({ JobName: jobName }).promise();
  }
}
