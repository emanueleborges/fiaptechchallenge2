// aws.service.ts
import { Injectable } from '@nestjs/common';
import { S3 } from 'aws-sdk';
import * as fs from 'fs';
import * as path from 'path';

@Injectable()
export class AwsService {
  private s3 = new S3({ region: process.env.AWS_REGION });

  async uploadToS3(filePath: string, bucket: string, key: string): Promise<void> {
    const fileContent = fs.readFileSync(filePath);
    await this.s3.putObject({
      Bucket: bucket,
      Key: key,
      Body: fileContent,
      ContentType: 'application/json',
    }).promise();
  }
}
